import logging
import os
from neonize.utils import log
import signal
from neonize.client import NewClient
from neonize.events import (
    MessageEv,
    ConnectedEv,
    HistorySyncEv,
    PairStatusEv,
    event
)
from neonize.utils.enum import Presence
from database import init_db
from whatsapp import on_message, on_history_sync, on_message
from config import CONV_DB_PATH, NEO_DB_PATH

def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def main():
    configure_logging()
    log.setLevel(logging.DEBUG)

    # A global event to handle interrupts
    stop_event = event

    def interrupted(*_):
        """Signal handler for Ctrl+C."""
        stop_event.set()

    signal.signal(signal.SIGINT, interrupted)

    # Create the DB directory if it doesn't exist
    os.makedirs(os.path.dirname(CONV_DB_PATH), exist_ok=True)
    os.makedirs("messages", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("converted", exist_ok=True)

    # Initialize DB
    init_db()

    # Create the client
    client = NewClient(NEO_DB_PATH)

    @client.event(ConnectedEv)
    def on_connected(client: NewClient, connected: ConnectedEv):
        client.send_presence(presence=Presence.AVAILABLE)
        logging.info("✓ Connected")

    @client.event(HistorySyncEv)
    def handle_history_sync(client: NewClient, history: HistorySyncEv):
        on_history_sync(client, history)

    @client.event(PairStatusEv)
    def pair_status(_: NewClient, message: PairStatusEv):
        logging.info(f"logged as {message.ID.User}")

    @client.event(MessageEv)
    def message_event(client: NewClient, message: MessageEv):
        on_message(client, message)

    # Connect the client
    client.connect()

    # Keep the program running until a signal is received
    stop_event.wait()
    logging.info("Exiting...")

if __name__ == "__main__":
    main()
