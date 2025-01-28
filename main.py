import logging
import os
import signal
import sys
from neonize.client import NewClient
from neonize.events import (
    ConnectedEv,
    MessageEv,
    PairStatusEv,
    event,
    HistorySyncEv
)
from neonize.utils import log
from neonize.utils.enum import ReceiptType

from database import init_db, save_message, get_messages

sys.path.insert(0, os.getcwd())

def interrupted(*_):
    event.set()

log.setLevel(logging.DEBUG)
signal.signal(signal.SIGINT, interrupted)

init_db()

client = NewClient("db/neonize.sqlite3")

@client.event(ConnectedEv)
def on_connected(client: NewClient, connected: ConnectedEv):
    log.info("⚡ Connected")

@client.event(HistorySyncEv)
def on_history_sync(client: NewClient, history: HistorySyncEv):
    """
    Processes historical messages from the sync data, storing them in the DB.
    The data structure is at `history.Data.conversations[...]`.
    """
    sync_type = getattr(history.Data, "syncType", None)
    log.info(f"Received history sync event with syncType: {sync_type}")

    # If no conversations, nothing to do
    if not hasattr(history.Data, "conversations"):
        log.info("No conversations found in HistorySyncEv.")
        return

    # Iterate over each conversation
    for conversation in history.Data.conversations:
        user_id = conversation.ID.split('@')[0]  # Extract phone number as user_id

        # Each conversation can have multiple messages
        for message_obj in conversation.messages:
            message_data = message_obj.message  # This includes both 'key' and 'message'
            msg = message_data.message  # The actual message content

            # Extract 'from_me' correctly from 'key'
            from_me = getattr(message_data.key, "fromMe", False)

            # Extract message content
            if hasattr(msg, "conversation") and msg.conversation:
                message_content = msg.conversation
            elif hasattr(msg, "extendedTextMessage") and msg.extendedTextMessage.text:
                message_content = msg.extendedTextMessage.text
            else:
                # If there's no plain text, skip the message
                log.debug(f"Skipping non-text historical message with ID: {message_data.key.ID}")
                continue

            # Extract timestamp
            timestamp = message_obj.message.messageTimestamp

            # Save message to the database
            save_message(user_id, message_content, timestamp, from_me)
            log.debug(f"Saved historical message from {user_id}: {message_content} at {timestamp} from_me={from_me}")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    """Handler for real-time incoming messages (outside of history sync)."""
    # You can optionally store these messages in the DB as well.
    chat = message.Info.MessageSource.Chat
    text = message.Message.conversation or message.Message.extendedTextMessage.text
    sender_name = message.Info.Pushname
    sender_id = message.Info.MessageSource.Chat.User
    log.info(f"Message from {sender_name} ({sender_id}): {text}")

    # Example: Save the newly received message
    from_me = message.Info.MessageSource.IsFromMe  # Typically False for an incoming message
    timestamp = message.Info.Timestamp // 1000  # Convert ms to s if needed

    # Save to DB, ignoring duplicates
    save_message(sender_id, text, timestamp, from_me)

    # Respond
    reply_text = "Hei, tässä on vastauksesi"
    client.send_message(chat, reply_text)
    # Optionally store your reply as well
    from_me_reply = True
    save_message(sender_id, reply_text, int(timestamp)+1, from_me_reply)  # or use current time

    # Mark as read
    client.mark_read(message.Info.ID,
                     chat=message.Info.MessageSource.Chat,
                     sender=message.Info.MessageSource.Sender,
                     receipt=ReceiptType.READ)

@client.event(PairStatusEv)
def PairStatusMessage(_: NewClient, message: PairStatusEv):
    log.info(f"logged as {message.ID.User}")

if __name__ == "__main__":
    client.connect()