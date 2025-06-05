import time
from neonize.client import NewClient
from neonize.events import MessageEv, HistorySyncEv
from neonize.utils.enum import ReceiptType
from neonize.utils import log
from database import save_message, get_messages, delete_messages
import os
from llm import (
    generate_final_response,
    generate_first_time_greeting
)
from config import ADMIN_NUMBER, AI_ASSISTANT_NAME
import pdfplumber
from docx import Document
from prompts import GREETING_PROMPT, FINAL_RESPONSE_PROMPT

is_bot_running = True
custom_prompts = {
    "greeting": GREETING_PROMPT,
    "final_response": FINAL_RESPONSE_PROMPT
}
bot_name = AI_ASSISTANT_NAME

# --- Helper functions ---
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

def handle_greeting(client: NewClient, chat, sender_id, sender_name, text):
    """Handles first-time greeting for a new conversation."""
    greeting = generate_first_time_greeting(sender_name, text, custom_prompts["greeting"])
    client.send_message(chat, greeting)
    log.info(f"Sent greeting to {sender_name} ({sender_id}).")
    save_message(sender_id, greeting, int(time.time()), True)

def handle_file(client: NewClient, sender_id, message):
    """Handles file attachments (downloads the file)."""
    if sender_id != ADMIN_NUMBER:
        log.info(f"Files from {sender_id} are not allowed.")
        return False

    file_name = (message.Message.documentMessage.fileName or
                 message.Message.imageMessage.fileName or "file")
    client.download_any(message=message.Message, path=f"./downloads/{file_name}")
    log.info(f"Downloaded file: {file_name}")

    file_extension = os.path.splitext(file_name)[1].lower()

    if file_extension == ".pdf":
        submission_markdown = convert_pdf_to_markdown(f"./downloads/{file_name}")
    elif file_extension == ".docx":
        submission_markdown = convert_docx_to_markdown(f"./downloads/{file_name}")
    elif file_extension == ".txt":
        with open(f"./downloads/{file_name}", "r", encoding="utf-8") as f:
            submission_markdown = f.read()
    else:
        client.send_message(message.Info.MessageSource.Chat, f"[SYSTEM] Unsupported file type: {file_extension}")
        return

    base_filename = os.path.splitext(os.path.basename(file_name))[0]
    txt_filename = f"{base_filename}.txt"
    txt_filepath = os.path.join("converted", txt_filename)
    try:
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(submission_markdown)
        print(f"Converted file saved to: {txt_filepath}")
        client.send_message(message.Info.MessageSource.Chat, f"[SYSTEM] File is saved and will be injected into context.")
    except Exception as e:
        print(f"Error saving redacted submission: {e}")
        client.send_message(message.Info.MessageSource.Chat, f"[SYSTEM] Error saving file: {e}")

    return True

def handle_commands(client: NewClient, chat, sender_id, text: str) -> bool:
    """
    Checks for special commands. If one of the commands is detected and the sender's number
    matches a specific number, it sends back pre-formatted info and returns True.
    """
    if not text.startswith("!") or not text.strip():
        return

    if sender_id != ADMIN_NUMBER:
        log.info(f"Command {text} from {sender_id} not allowed.")
        return False

    log.info(f"Command {text} from {sender_id} is allowed.")
    global is_bot_running, custom_prompts, bot_name

    if text.startswith("!files"):
        # Get list of files in the downloads folder
        downloads_folder = "./downloads"
        files = os.listdir(downloads_folder)
        files_list = "\n".join(files)
        client.send_message(chat, f"[COMMAND] Files in folder:\n{files_list}")
        log.info(f"Processed !files command for {sender_id}.")
        return True
    elif text.startswith("!removefile"):
        # Remove a file from the downloads folder
        parts = text.split(" ", 1)
        if len(parts) < 2:
            client.send_message(chat, "[COMMAND] Please provide a filename to remove.")
            return True
        filename = parts[1]
        dl_path = os.path.join("./downloads", filename)
        base_filename = os.path.splitext(os.path.basename(filename))[0]
        txt_filename = f"{base_filename}.txt"
        conv_path = os.path.join("./converted", txt_filename)
        if os.path.exists(dl_path):
            os.remove(dl_path)
            if os.path.exists(conv_path):
                os.remove(conv_path)
            client.send_message(chat, f"[COMMAND] Removed file: {filename}")
        else:
            client.send_message(chat, f"[COMMAND] File not found: {filename}")
        log.info(f"Processed !removefile command for {sender_id} and file {filename}.")
        return True
    elif text.startswith("!commands"):
        commands = ["!commands - Show available commands",
                    "!files - List files in the downloads folder",
                    "!removefile <filename> - Remove a file from the downloads folder",
                    "!prompts - Show available prompts",
                    "!editprompt <prompt_name> <new_prompt_content> - Edit a prompt",
                    "!renamebot <new_bot_name> - Rename the bot",
                    "!reset - Clear conversation history for your number",
                    "!pause - Pause the bot",
                    "!resume - Resume the bot",
                    "!permanentstop - Stop the bot permanently"]
        commands_joined = "\n".join(commands)
        client.send_message(chat, f"[COMMAND] Available commands:\n{commands_joined}")
        log.info(f"Processed !commands command for {sender_id}.")
        return True
    elif text.startswith("!prompts"):
        prompts = [f"greeting: {custom_prompts['greeting']}", f"final_response: {custom_prompts['final_response']}"]
        prompts_joined = "\n".join(prompts)
        client.send_message(chat, f"[COMMAND] Prompts:\n\n{prompts_joined}")
        log.info(f"Processed !prompts command for {sender_id}.")
        return True
    elif text.startswith("!editprompt"):
        parts = text.split(" ", 2)
        if len(parts) < 3:
            client.send_message(chat, "[COMMAND] Please provide a prompt name and new prompt content.")
            return True
        prompt_name = parts[1]
        new_prompt_content = parts[2]
        if prompt_name not in custom_prompts:
            client.send_message(chat, f"[COMMAND] Unknown prompt: {prompt_name}. Please use !prompts to see available prompts.")
            return True
        custom_prompts[prompt_name] = new_prompt_content
        client.send_message(chat, f"[COMMAND] Updated prompt {prompt_name}.")
        log.info(f"Processed !editprompt command for {sender_id} and prompt {prompt_name}.")
        return True
    elif text.startswith("!renamebot"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            client.send_message(chat, "[COMMAND] Please provide a new bot name.")
            return True
        new_bot_name = parts[1]
        bot_name = new_bot_name
        client.send_message(chat, f"[COMMAND] Bot name updated to: {new_bot_name}.")
        log.info(f"Processed !renamebot command for {sender_id}.")
        return True
    elif text.startswith("!reset"):
        client.send_message(chat, "[COMMAND] Cleared conversation history!")
        delete_messages(sender_id)
        log.info(f"Cleared conversation history for {sender_id} due to '!reset' command.")
        return True
    elif text.startswith("!pause"):
        client.send_message(chat, "[COMMAND] The bot is now paused!")
        is_bot_running = False
        log.info(f"Processed !pause command for {sender_id}.")
        return True
    elif text.startswith("!resume"):
        client.send_message(chat, "[COMMAND] The bot has now resumed operations!")
        is_bot_running = True
        log.info(f"Processed !resume command for {sender_id}.")
        return True
    elif text.startswith("!permanentstop"):
        client.send_message(chat, "[COMMAND] The bot is shutting down!")
        log.info(f"Processed !permanentstop command for {sender_id}.")
        os._exit(0)
        return True
    elif text.startswith("!"):
        client.send_message(chat, "[COMMAND] Unknown command. Please use !commands to see available commands.")
        log.info(f"Processed unknown command for {sender_id}.")
        return True

    return False

def handle_final_response(client: NewClient, chat, sender_id, text):
    """Generates and sends the final response using the LLM."""
    final_answer = generate_final_response(
        user_id=sender_id,
        user_text=text,
        custom_prompt=custom_prompts["final_response"]
    )
    log.debug(f"Final answer generated: {final_answer}")
    if not final_answer.strip():
        log.info(f"No final response generated for {sender_id}.")
        #client.send_message(chat, "I'm sorry, I couldn't generate a response for you.")
        return
    client.send_message(chat, final_answer)
    save_message(sender_id, final_answer, int(time.time()), True)
    log.info(f"Sent final response to {sender_id}.")

def on_history_sync(client: NewClient, history: HistorySyncEv):
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
        timestamp = message.Info.Timestamp // 1000  # Convert ms to s if needed
        sender_name = message.Info.Pushname or "User"

        log.info(f"Message from {sender_name} ({sender_id}): {text}")

        # Check if the message is older than one minute
        if time.time() - timestamp > 60:
            log.info(f"Message from {sender_name} ({sender_id}) is older than one minute; skipping.")
            return

        # Mark as read
        client.mark_read(
            message.Info.ID,
            chat=chat,
            sender=message.Info.MessageSource.Sender,
            receipt=ReceiptType.READ
        )
        log.debug(f"Marked message {message.Info.ID} as read.")

        # Save the incoming message to the DB
        save_message(sender_id, text, timestamp, from_me)
        log.debug(f"Saved incoming message for user {sender_id} at timestamp {timestamp}.")

        # Check for a command and process it if present.
        if handle_commands(client, chat, sender_id, text):
            # If a command was processed, do not process further.
            return

        # Process file attachments if present
        if message.Info.Type == "media" and not message.Info.MediaType == "url":
            if handle_file(client, sender_id, message):
                return

        if not is_bot_running:
            log.info("Bot is paused; skipping message processing.")
            return

        # Determine if this is the first message from the user
        previous_messages = get_messages(sender_id)
        is_first_message = len(previous_messages) == 0
        log.debug(f"User {sender_id} has {len(previous_messages)} previous messages; is_first_message={is_first_message}")

        # Process greeting for a first-time message
        if is_first_message:
            handle_greeting(client, chat, sender_id, sender_name, text)

        log.info(f"Generating final response for {sender_id}...")
        handle_final_response(client, chat, sender_id, text)

    except Exception as e:
        log.error(f"Error in on_message handler: {e}")
