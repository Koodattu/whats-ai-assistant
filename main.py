# main.py
import logging
import os
import signal
import sys
from neonize.client import NewClient
from neonize.events import (
    MessageEv,
    ConnectedEv,
    HistorySyncEv,
    PairStatusEv,
    event
)
from neonize.utils import log

# Import our custom handlers
from database import init_db
from whatsapp import on_message, on_history_sync, on_message

# Optional config if you want
from config import CONV_DB_PATH, NEO_DB_PATH

sys.path.insert(0, os.getcwd())

# A global event to handle interrupts
stop_event = event

def interrupted(*_):
    """Signal handler for Ctrl+C."""
    stop_event.set()

def main():
    # Initialize logging
    log.setLevel(logging.DEBUG)
    signal.signal(signal.SIGINT, interrupted)

    # Create the DB directory if it doesn't exist
    os.makedirs(os.path.dirname(CONV_DB_PATH), exist_ok=True)

    # Initialize DB
    init_db()

    # Create the client
    client = NewClient(NEO_DB_PATH)

    @client.event(ConnectedEv)
    def on_connected(client: NewClient, connected: ConnectedEv):
        log.info("⚡ Connected")

    @client.event(HistorySyncEv)
    def handle_history_sync(client: NewClient, history: HistorySyncEv):
        on_history_sync(client, history)

    @client.event(PairStatusEv)
    def PairStatusMessage(_: NewClient, message: PairStatusEv):
        log.info(f"logged as {message.ID.User}")

    @client.event(MessageEv)
    def PairStatusMessage(client: NewClient, message: MessageEv):
        on_message(client, message)

    # Connect the client
    client.connect()

    # Keep the program running until a signal is received
    stop_event.wait()
    log.info("Exiting...")

if __name__ == "__main__":
    main()
