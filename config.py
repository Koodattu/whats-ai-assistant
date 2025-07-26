import os
from dotenv import load_dotenv

load_dotenv()

AI_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "KoodattuBotti")
SCENARIO = os.getenv("SCENARIO", "base")

OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini-2025-04-14")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CONV_DB_PATH = "db/conversations.sqlite3"
NEO_DB_PATH = "db/neonize.sqlite3"
MAX_MESSAGES = 10
SKIP_HISTORY_SYNC = True
SCRAPE_USER_LINKS = False
DOWNLOAD_USER_FILES = False