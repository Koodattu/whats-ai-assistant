import os
from dotenv import load_dotenv
load_dotenv()

# Database Configuration
CONV_DB_PATH = "db/conversations.sqlite3"
NEO_DB_PATH = "db/neonize.sqlite3"

# "ollama" or "openai" or "openrouter"
LLM_PROVIDER = "openrouter"

# Local Language Model Configuration
OLLAMA_MODEL_NAME = "hf.co/itlwas/Ahma-7B-Instruct-Q4_K_M-GGUF:latest"

# OpenAI Language Model Configuration
OPENAI_MODEL_NAME = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenRouter Language Model Configuration
OPENROUTER_MODEL_NAME = "openai/gpt-4o-mini"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Prompt Configuration
CONV_DB_PATH = "db/conversations.sqlite3"
NEO_DB_PATH = "db/neonize.sqlite3"
MAX_MESSAGES = 5

# AI Assistant Configuration
AI_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER")