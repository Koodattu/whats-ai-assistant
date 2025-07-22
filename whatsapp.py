# whatsapp.py
import re
import time
from collections import defaultdict, deque
from neonize.client import NewClient, JID
from neonize.events import MessageEv, HistorySyncEv
from neonize.utils.enum import ReceiptType, ChatPresence, ChatPresenceMedia
from neonize.utils import log
import pdfplumber
from docx import Document
from database import save_message, get_messages, delete_messages, get_recent_messages_formatted
from scraping import scrape_text
import os
from llm import (
    generate_wait_message,
    generate_final_response
)

USER_SCRAPED_CONTENT = {}

# Rate limiting: user_id -> deque of timestamps (seconds)
user_message_timestamps = defaultdict(lambda: deque(maxlen=5))

def can_respond_to_user(user_id):
    now = time.time()
    timestamps = user_message_timestamps[user_id]
    # Remove timestamps older than 30 seconds
    while timestamps and now - timestamps[0] > 30:
        timestamps.popleft()
    return len(timestamps) < 5

def record_user_response(user_id):
    user_message_timestamps[user_id].append(time.time())

def handle_link(client: NewClient, message: MessageEv, sender_id, sender_name, text):
    """Handles link detection and scraping."""
    url_pattern = r'(https?://\S+)'
    links_found = re.findall(url_pattern, text)
    if not links_found:
        return

    link = links_found[0]
    log.info(f"Link detected: {link}")

    # Send wait message
    wait_message = generate_wait_message(text)
    client.reply_message(wait_message, message)
    save_message(sender_id, wait_message, int(time.time()), True)
    log.info(f"Sent wait message to {sender_name} for link processing: {wait_message}")

    # Scrape the link and store the content
    scraped_content = scrape_text(link)
    log.debug(f"Scraped content (first 200 chars): {scraped_content[:200]}...")
    USER_SCRAPED_CONTENT[sender_id] = f"\n[Scraped from {link}]\n{scraped_content}"
    log.info(f"Updated scraped content for {sender_id}.")


def convert_pdf_to_markdown(pdf_path):
    """Converts a PDF file to markdown text."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            markdown_lines = []
            for page_num, page in enumerate(pdf.pages, start=1):
                markdown_lines.append(f"## Page {page_num}\n")
                text = page.extract_text()
                if text:
                    markdown_lines.append(text.strip() + "\n")
                else:
                    markdown_lines.append("*(No text could be extracted from this page)*\n")
            return "\n".join(markdown_lines)
    except Exception as e:
        return f"Error reading PDF: {e}"

def convert_docx_to_markdown(docx_path):
    """Converts a DOCX file to markdown text."""
    try:
        document = Document(docx_path)
        markdown_text = ""
        for paragraph in document.paragraphs:
            markdown_text += paragraph.text + "\n"
        return markdown_text
    except Exception as e:
        return f"Error reading DOCX: {e}"

def handle_file(client: NewClient, message: MessageEv):
    """Handles file attachments (downloads the file, converts, and saves as text)."""
    file_name = (getattr(message.Message.documentMessage, 'fileName', None) or
                 getattr(message.Message.imageMessage, 'fileName', None) or "file")
    chat = message.Info.MessageSource.Chat
    client.send_message(chat, f"[SYSTEM] Processing file: {file_name}...")
    try:
        client.download_any(message=message.Message, path=f"./downloads/{file_name}")
        log.info(f"Downloaded file: {file_name}")
    except Exception as e:
        log.error(f"Failed to download file: {e}")
        client.send_message(chat, f"[SYSTEM] Failed to download file: {e}")
        return

    file_extension = os.path.splitext(file_name)[1].lower()
    submission_markdown = None
    if file_extension == ".pdf":
        submission_markdown = convert_pdf_to_markdown(f"./downloads/{file_name}")
    elif file_extension == ".docx":
        submission_markdown = convert_docx_to_markdown(f"./downloads/{file_name}")
    elif file_extension == ".txt":
        try:
            with open(f"./downloads/{file_name}", "r", encoding="utf-8") as f:
                submission_markdown = f.read()
        except Exception as e:
            submission_markdown = f"Error reading TXT: {e}"
    else:
        client.send_message(chat, f"[SYSTEM] File type '{file_extension}' is not supported.")
        return

    base_filename = os.path.splitext(os.path.basename(file_name))[0]
    txt_filename = f"{base_filename}.txt"
    txt_filepath = os.path.join("converted", txt_filename)
    try:
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(submission_markdown)
        log.info(f"Converted file saved to: {txt_filepath}")
        client.send_message(chat, f"[SYSTEM] File processed and saved for future use.")
    except Exception as e:
        log.error(f"Error saving converted file: {e}")
        client.send_message(chat, f"[SYSTEM] Error saving converted file: {e}")
    return

def handle_commands(client: NewClient, chat: JID, sender_id: str, text: str):
    """
    Checks for special commands. If one of the commands is detected and the sender's number
    matches a specific number, it sends back pre-formatted info and returns True.
    """
    log.debug(f"Command {text} from {sender_id} is allowed.")

    if text.startswith("!reset"):
        client.send_message(chat, "[SYSTEM] Cleared conversation history!")
        delete_messages(sender_id)
        log.info(f"Cleared conversation history for {sender_id} due to '!reset' command.")
        USER_SCRAPED_CONTENT[sender_id] = ""
        log.debug(f"Cleared scraped content for {sender_id}.")
        return True

    return False

def handle_final_response(client: NewClient, chat: JID, sender_id: str, text: str):
    """Generates and sends the final response using the LLM."""
    final_answer = generate_final_response(user_id=sender_id, scraped_text=USER_SCRAPED_CONTENT.get(sender_id, ""), user_text=text)
    log.debug(f"Final answer generated: {final_answer}")
    client.send_message(to=chat, message=final_answer)
    save_message(user_id=sender_id, message=final_answer, timestamp=int(time.time()), from_me=True)
    log.info(f"Sent final response to {sender_id}.")

# --- Main event handlers ---

def on_history_sync(client, history: HistorySyncEv):
    """
    Processes historical messages from the sync data, storing them in the DB.
    The data structure is at `history.Data.conversations[...]`.
    """
    sync_type = getattr(history.Data, "syncType", None)
    log.info(f"Received history sync event with syncType: {sync_type}")
    log.debug(f"Full history sync data: {history}")

    if not hasattr(history.Data, "conversations"):
        log.info("No conversations found in HistorySyncEv.")
        return

    for conversation in history.Data.conversations:
        user_id = conversation.ID.split('@')[0]  # e.g. phone number
        log.debug(f"Processing conversation for user {user_id}")
        for message_obj in conversation.messages:
            message_data = message_obj.message
            msg = message_data.message
            from_me = getattr(message_data.key, "fromMe", False)
            log.debug(f"Processing message (from_me={from_me}): {msg}")

            # Extract text from different possible fields
            if hasattr(msg, "conversation") and msg.conversation:
                message_content = msg.conversation
            elif (hasattr(msg, "extendedTextMessage") and msg.extendedTextMessage.text):
                message_content = msg.extendedTextMessage.text
            else:
                log.debug("Message is not a text message; skipping.")
                continue

            timestamp = message_obj.message.messageTimestamp
            log.debug(f"Saving message with timestamp {timestamp} for user {user_id}")
            save_message(user_id, message_content, timestamp, from_me)

def on_message(client: NewClient, message: MessageEv):
    """
    Real-time incoming messages.
    Uses one big try/except to capture any errors and separates out key functionality
    into helper functions.
    """
    try:
        chat = message.Info.MessageSource.Chat
        sender_id = message.Info.MessageSource.Chat.User
        text = (message.Message.conversation or
                message.Message.extendedTextMessage.text or
                message.Message.imageMessage.caption or
                message.Message.documentMessage.caption or
                "")
        from_me = message.Info.MessageSource.IsFromMe
        timestamp = message.Info.Timestamp // 1000
        sender_name = message.Info.Pushname or "User"

        log.info(f"Message from {sender_name} ({sender_id}): {text}")
        log.debug(f"Raw message info: {message}")

        # Save raw message object to a file
        message_filename = f"messages/{int(time.time())}.txt"
        with open(message_filename, "w", encoding="utf-8") as file:
            file.write(str(message))
        log.debug(f"Saved raw message to {message_filename}")

        # Check if the message is older than one minute
        if time.time() - timestamp > 60:
            log.info(f"Message from {sender_name} ({sender_id}) is older than one minute; skipping further processing.")
            return

        # Mark as read
        client.mark_read(
            message.Info.ID,
            chat=chat,
            sender=message.Info.MessageSource.Sender,
            receipt=ReceiptType.READ
        )
        log.debug(f"Marked message {message.Info.ID} as read.")

        # Rate limiting: only respond if under the limit
        if not can_respond_to_user(sender_id):
            log.info(f"Rate limit reached for {sender_id}; skipping response.")
            return

        # Send typing notification (composing)
        client.send_chat_presence(jid=chat, state=ChatPresence.CHAT_PRESENCE_COMPOSING, media=ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT)

        # Check for a command and process it if present.
        if handle_commands(client, chat, sender_id, text):
            # If a command was processed, send paused notification and do not process further.
            client.send_chat_presence(jid=chat, state=ChatPresence.CHAT_PRESENCE_PAUSED, media=ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT)
            return

        # Save the incoming message to the DB
        save_message(sender_id, text, timestamp, from_me)
        log.debug(f"Saved incoming message for user {sender_id} at timestamp {timestamp}.")

        # Process links (if any)
        handle_link(client, message, sender_id, sender_name, text)

        # Process file attachments if present
        if message.Info.Type == "media" and not message.Info.MediaType == "url":
            handle_file(client, message)

        log.info(f"Generating final response for {sender_id}...")
        handle_final_response(client, chat, sender_id, text)
        record_user_response(sender_id)

        # After responding, send paused notification
        client.send_chat_presence(jid=chat, state=ChatPresence.CHAT_PRESENCE_PAUSED, media=ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT)

    except Exception as e:
        log.error(f"Error in on_message handler: {e}")
