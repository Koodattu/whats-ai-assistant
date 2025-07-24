import re
import time
import random
from collections import defaultdict, deque
import uuid
from neonize.client import NewClient, JID
from neonize.events import MessageEv, HistorySyncEv
from neonize.utils.enum import ReceiptType, ChatPresence, ChatPresenceMedia
from neonize.utils import log
import pdfplumber
from docx import Document
import threading
import queue
from database import save_message, delete_messages
from scraping import scrape_text
import os
from llm import (
    generate_wait_message,
    generate_final_response,
    generate_error_message
)
from tool_calls import (
    describe_image_with_gpt,
    poll_llm_for_tool_choice,
    text_to_speech_with_openai,
    generate_image_with_openai,
    edit_image_with_openai,
    transcribe_audio_with_whisper,
    web_search
)
from config import SKIP_HISTORY_SYNC
from filelogger import FileLogger
fileLogger = FileLogger()

# --- Session Content Item Class ---
class UserSessionContentItem:
    def __init__(self, type_: str, source: str, content: str):
        self.type = type_  # 'link', 'document', 'image'
        self.source = source  # filename or url
        self.content = content
    def __repr__(self):
        return f"[{self.type}] {self.source}: {self.content[:60]}..."

# Global message queue for processing incoming messages sequentially
message_queue = queue.Queue()

def process_message(client: NewClient, message: MessageEv):
    try:
        chat = message.Info.MessageSource.Chat
        sender_id = message.Info.MessageSource.Chat.User
        text = (message.Message.conversation or
                message.Message.extendedTextMessage.text or
                message.Message.imageMessage.caption or
                message.Message.documentMessage.caption or
                "")
        from_me = message.Info.MessageSource.IsFromMe
        is_group = message.Info.MessageSource.IsGroup
        is_edit = message.IsEdit
        is_viewonce = message.IsViewOnce or message.IsViewOnceV2 or message.IsViewOnceV2Extension
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

        # Skip messages from the bot itself
        if chat.User == sender_id and from_me:
            log.info(f"Skipping message from bot itself: {sender_id}")
            return

        # Skip group, edit, and view once messages
        if is_group or is_edit or is_viewonce:
            log.info(f"Skipping group/edit/view once message from {sender_id}.")
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
            text = handle_file(client, message, text, sender_id)

        log.info(f"Generating final response for {sender_id}...")
        handle_final_response(client, chat, sender_id, text)
        record_user_response(sender_id)

        # After responding, send paused notification
        client.send_chat_presence(jid=chat, state=ChatPresence.CHAT_PRESENCE_PAUSED, media=ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT)

    except Exception as e:
        log.error(f"Error in process_message handler: {e}")

USER_SCRAPED_CONTENT = defaultdict(list)  # user_id -> list of UserSessionContentItem

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
    wait_message = generate_wait_message(user_text=text, user_id=sender_id)
    time.sleep(random.uniform(2, 5))  # Add random delay before sending wait message
    client.reply_message(wait_message, message)
    save_message(sender_id, wait_message, int(time.time()), True)
    log.info(f"Sent wait message to {sender_name} for link processing: {wait_message}")

    # Scrape the link and store the content
    scraped_content = scrape_text(link)
    log.debug(f"Scraped content (first 200 chars): {scraped_content[:200]}...")
    # Add to session context
    USER_SCRAPED_CONTENT[sender_id].append(UserSessionContentItem(
        type_="link",
        source=link,
        content=scraped_content
    ))
    log.info(f"Added scraped link content for {sender_id}.")


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

def handle_file(client: NewClient, message: MessageEv, user_text: str, sender_id: str):
    """Handles file attachments (downloads the file, converts, and saves as text, and adds to session context)."""
    log.info(f"Handling file attachment for user {sender_id}.")
    file_name = None
    document_msg = getattr(message.Message, "documentMessage", None)
    image_msg = getattr(message.Message, "imageMessage", None)
    audio_msg = getattr(message.Message, "audioMessage", None)
    if document_msg and getattr(document_msg, "fileName", None):
        log.info("Processing document message.")
        file_name = document_msg.fileName
    elif image_msg and "jpeg" in getattr(image_msg, "mimetype", None):
        log.info("Processing image message.")
        file_name = f"{int(time.time())}_{uuid.uuid4()}.jpeg"
    elif audio_msg and "audio" in getattr(audio_msg, "mimetype", None):
        log.info("Processing audio message.")
        file_name = f"{int(time.time())}_{uuid.uuid4()}.ogg"
    else:
        log.info("Unknown message type; skipping file handling.")

    if not file_name:
        log.info("No file name found in the message; skipping file handling.")
        return

    log.info(f"File name detected: {file_name}")
    chat = message.Info.MessageSource.Chat

    try:
        client.download_any(message=message.Message, path=f"./downloads/{file_name}")
        log.info(f"Downloaded file: {file_name}")
    except Exception as e:
        log.error(f"Failed to download file: {e}")
        client.send_message(chat, generate_error_message(user_text=user_text, user_id=sender_id))
        return

    file_extension = os.path.splitext(file_name)[1].lower()
    submission_markdown = None
    item_type = None
    if file_extension == ".jpeg":
        submission_markdown = describe_image_with_gpt(f"./downloads/{file_name}")
        item_type = "image"
    elif file_extension == ".ogg":
        submission_markdown = transcribe_audio_with_whisper(f"./downloads/{file_name}")
        item_type = "audio"
        return submission_markdown  # Return early for audio files
    elif file_extension == ".pdf":
        submission_markdown = convert_pdf_to_markdown(f"./downloads/{file_name}")
        item_type = "document"
    elif file_extension == ".docx":
        submission_markdown = convert_docx_to_markdown(f"./downloads/{file_name}")
        item_type = "document"
    elif file_extension == ".txt":
        try:
            with open(f"./downloads/{file_name}", "r", encoding="utf-8") as f:
                submission_markdown = f.read()
            item_type = "document"
        except Exception as e:
            submission_markdown = f"Error reading TXT: {e}"
            item_type = "document"
    else:
        log.error(f"Unsupported file type: {file_extension}")
        client.send_message(chat, generate_error_message(user_text=user_text, user_id=sender_id))
        return

    if not item_type == "audio":
        # Add to session context
        USER_SCRAPED_CONTENT[sender_id].append(UserSessionContentItem(
            type_=item_type,
            source=file_name,
            content=submission_markdown
        ))

    if item_type == "document":
        log.info(f"Added document content for {sender_id}.")
        base_filename = os.path.splitext(os.path.basename(file_name))[0]
        txt_filename = f"{base_filename}.txt"
        txt_filepath = os.path.join("converted", txt_filename)
        try:
            with open(txt_filepath, "w", encoding="utf-8") as f:
                f.write(submission_markdown)
            log.info(f"Converted file saved to: {txt_filepath}")
        except Exception as e:
            log.error(f"Error saving converted file: {e}")

    return user_text


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
    # Start timer for total response delay
    min_total_delay = random.uniform(2, 5)
    start_time = time.time()
    # Concatenate all session content for user
    session_items = USER_SCRAPED_CONTENT.get(sender_id, [])
    scraped_text = "\n".join([
        f"[{item.type.upper()}] {item.source}\n{item.content}" for item in session_items
    ])
    tool_usage_result = process_llm_tools(text, client, chat)
    final_answer = generate_final_response(user_id=sender_id, scraped_text=scraped_text, user_text=text, tool_usage_result=tool_usage_result)
    log.debug(f"Final answer generated: {final_answer}")
    elapsed = time.time() - start_time
    remaining = min_total_delay - elapsed
    if remaining > 0:
        time.sleep(remaining)
    client.send_message(to=chat, message=final_answer)
    save_message(user_id=sender_id, message_content=final_answer, timestamp=int(time.time()), from_me=True)
    log.info(f"Sent final response to {sender_id}.")

def process_llm_tools(user_message: str, client: NewClient, chat: JID):
    """
    Handles entire LLM tool processing flow.
    """
    tool_call = poll_llm_for_tool_choice(user_message)
    if not tool_call:
        log.info("No tool calls needed for user message.")
        return "No tool calls needed."

    if tool_call.function.name == "web_search_tool":
        log.info("Processing web search tool call.")
        search_query = getattr(tool_call.function.parsed_arguments, "query", None)
        if not search_query:
            log.error("No search query provided in tool call arguments.")
            return "No search query provided."
        # Call the web search tool
        search_results = web_search(search_query)
        log.debug(f"Web search results: {search_results}")
        # Here you would process the search results and return them
        result_strings = []
        for result in search_results:
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            result_strings.append(f"{url}\n{snippet}\n")
        return tool_call.function.name + ": " + "\n".join(result_strings)
    elif tool_call.function.name == "generate_tts_tool":
        log.info("Processing text-to-speech tool call.")
        text = getattr(tool_call.function.parsed_arguments, "text", None)
        if not text:
            log.error("No text provided for TTS generation.")
            return "No text provided for TTS generation."
        audio_path = text_to_speech_with_openai(text)
        if not audio_path:
            return "Error generating audio."
        client.send_audio(chat, audio_path)
        # Here you would handle the audio file, e.g., save or send it
        return f"{tool_call.function.name}: Audio generated successfully. It will be sent before this message. Please act like you just generated and sent the audio successfully for the user."
    elif tool_call.function.name == "generate_image_tool":
        log.info("Processing image generation tool call.")
        prompt = getattr(tool_call.function.parsed_arguments, "prompt", None)
        if not prompt:
            log.error("No prompt provided for image generation.")
            return "No prompt provided for image generation."
        # Call the image generation tool, it returns the filepath
        client.send_message(chat, generate_wait_message(user_text=user_message, user_id=chat.User))
        image_path = generate_image_with_openai(prompt)
        if not image_path:
            return "Error generating image."
        client.send_image(chat, image_path)
        # Here you would handle the image file, e.g., save or send it
        return f"{tool_call.function.name}: Image generated successfully. It will be sent before this message. Please act like you just generated and sent the image successfully for the user."
    elif tool_call.function.name == "edit_image_tool":
        # TODO
        log.info("Processing image editing tool call.")
        prompt = getattr(tool_call.function.parsed_arguments, "prompt", None)
        if not image_path or not prompt:
            log.error("Missing image path or prompt for image editing.")
            return "Missing image path or prompt for image editing."
        # Call the image editing tool, it returns the filepath
        client.send_message(chat, generate_wait_message(user_text=user_message, user_id=chat.User))
        edited_image_path = edit_image_with_openai(image_path, prompt)
        if not edited_image_path:
            return "Error editing image."
        client.send_image(chat, edited_image_path)
        # Here you would handle the edited image file, e.g., save or send it
        return f"{tool_call.function.name}: Image edited successfully. It will be sent before this message. Please act like you just generated and sent the edited image successfully for the user."
    return "Something went wrong with tool processing."

# --- Main event handlers ---

def on_history_sync(client: NewClient, history: HistorySyncEv):
    """
    Processes historical messages from the sync data, storing them in the DB.
    The data structure is at `history.Data.conversations[...]`.
    """
    if SKIP_HISTORY_SYNC:
        log.info("Skipping history sync due to configuration.")
        return

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
    Enqueue incoming messages for sequential processing.
    """
    message_queue.put((client, message))
    fileLogger.log(f"[NEW_MESSAGE] {message}")

# Start the message worker thread
def message_worker():
    while True:
        client, message = message_queue.get()
        try:
            process_message(client, message)
        except Exception as e:
            log.error(f"Error processing message: {e}")
        finally:
            message_queue.task_done()

threading.Thread(target=message_worker, daemon=True).start()
