import os
from dotenv import load_dotenv

load_dotenv()

AI_ASSISTANT_NAME = os.getenv("AI_ASSISTANT_NAME")

OPENAI_API_URL = os.getenv("OPENAI_API_URL")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CONV_DB_PATH = "db/conversations.sqlite3"
NEO_DB_PATH = "db/neonize.sqlite3"
MAX_MESSAGES = 10

FINAL_RESPONSE_PROMPT = """\
You are a friendly assistant called {ai_assistant_name}, an expert at helping users without wasting their time.
Always respond in the same language as the user's last message.
Keep your response short and concise, unless the user explicitly requests a longer or more detailed explanation.

Here is the previous conversation for context:
--------------------------------
{previous_messages}
--------------------------------

If the user provided a link, I opened the link for you and heres the text it contained:
--------------------------------
{scraped_text}
--------------------------------

Now, the user's latest message is:
--------------------------------
{user_message}
--------------------------------

Please provide a short, friendly, helpful response in the same language as the user's message.
It's ok to admit that you do not know something.
Use the user's latest message and the summary to determine the language.
If the user included questions about the link, address them specifically.
Otherwise, politely offer to clarify or answer further questions.
"""