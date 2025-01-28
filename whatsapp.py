# whatsapp.py
import re
import time
from neonize.client import NewClient
from neonize.events import MessageEv, HistorySyncEv
from neonize.utils.enum import ReceiptType
from neonize.utils import log
from database import save_message, get_messages
from scraping import scrape_text
from llm import (
    summarize_conversation,
    generate_wait_message,
    generate_final_response,
    generate_first_time_greeting
)

# A simple in-memory dictionary to store scraped link content per user
#   { user_id: "accumulated scraped text" }
USER_SCRAPED_CONTENT = {}

def on_history_sync(client, history: HistorySyncEv):
    """
    Processes historical messages from the sync data, storing them in the DB.
    The data structure is at `history.Data.conversations[...]`.
    """
    sync_type = getattr(history.Data, "syncType", None)
    log.info(f"Received history sync event with syncType: {sync_type}")

    if not hasattr(history.Data, "conversations"):
        log.info("No conversations found in HistorySyncEv.")
        return

    for conversation in history.Data.conversations:
        user_id = conversation.ID.split('@')[0]  # e.g. phone number
        for message_obj in conversation.messages:
            message_data = message_obj.message
            msg = message_data.message
            from_me = getattr(message_data.key, "fromMe", False)

            # Extract text
            if hasattr(msg, "conversation") and msg.conversation:
                message_content = msg.conversation
            elif (
                hasattr(msg, "extendedTextMessage") 
                and msg.extendedTextMessage.text
            ):
                message_content = msg.extendedTextMessage.text
            else:
                # Not text
                continue

            timestamp = message_obj.message.messageTimestamp
            save_message(user_id, message_content, timestamp, from_me)

def on_message(client: NewClient, message: MessageEv):
    """
    Real-time incoming messages.
    """
    chat = message.Info.MessageSource.Chat
    sender_id = message.Info.MessageSource.Chat.User
    text = (
        message.Message.conversation 
        or message.Message.extendedTextMessage.text 
        or ""
    )
    from_me = message.Info.MessageSource.IsFromMe
    timestamp = message.Info.Timestamp // 1000  # Convert ms to s if needed
    sender_name = message.Info.Pushname or "User"

    log.info(f"Message from {sender_name} ({sender_id}): {text}")

    # Mark as read
    client.mark_read(
        message.Info.ID,
        chat=chat,
        sender=message.Info.MessageSource.Sender,
        receipt=ReceiptType.READ
    )

    # Check if this is the first message from the user
    previous_messages = get_messages(sender_id)
    is_first_message = len(previous_messages) == 0

    if is_first_message:
        # Generate the greeting using the new function, including the user's message
        greeting = generate_first_time_greeting(sender_name, text)

        # Send the greeting to the user
        client.send_message(chat, greeting)
        log.info(f"Sent greeting to {sender_name} ({sender_id}): {greeting}")

        # Save the greeting message to the DB
        save_message(sender_id, greeting, int(time.time()), True)

    # Save incoming to DB
    save_message(sender_id, text, timestamp, from_me)

    # Check if text contains a link.
    url_pattern = r'(https?://\S+)'
    links_found = re.findall(url_pattern, text)

    if links_found:
        # Handle link case
        link = links_found[0]

        # (1) Send a "wait" message
        wait_message = generate_wait_message(text)
        client.reply_message(wait_message, message)
        save_message(sender_id, wait_message, int(time.time()), True)

        # (2) Scrape the link
        scraped_content = scrape_text(link)

        # (3) Store/accumulate scraped content
        if sender_id not in USER_SCRAPED_CONTENT:
            USER_SCRAPED_CONTENT[sender_id] = ""
        USER_SCRAPED_CONTENT[sender_id] += f"\n[Scraped from {link}]\n{scraped_content}"

    # Summarize the most recent messages
    conversation_summary = summarize_conversation(sender_id)

    # Generate the final response
    final_answer = generate_final_response(
        conversation_summary=conversation_summary,
        scraped_text=USER_SCRAPED_CONTENT.get(sender_id, ""),
        user_text=text
    )

    # Send the final response
    client.send_message(chat, final_answer)
    save_message(sender_id, final_answer, int(time.time()), True)
