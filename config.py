import os
from dotenv import load_dotenv
load_dotenv()

# Database Configuration
CONV_DB_PATH = "db/conversations.sqlite3"
NEO_DB_PATH = "db/neonize.sqlite3"

# "ollama" or "openai" or "openrouter" or "azure"
LLM_PROVIDER = os.getenv("LLM_PROVIDER")

# Azure configuration
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")
AZURE_SUBSCRIPTION_KEY = os.getenv("AZURE_SUBSCRIPTION_KEY")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION")

# Prompt Configuration
MAX_MESSAGES = os.getenv("MAX_MESSAGES", 5)

# AI Assistant Configuration
AI_ASSISTANT_NAME = os.getenv("ASSISTANT_NAME")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER")