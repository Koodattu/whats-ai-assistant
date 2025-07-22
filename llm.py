# llm.py
import requests
import logging
from config import (
    OPENAI_API_KEY,
    OPENAI_API_URL,
    OPENAI_MODEL_NAME,
    FINAL_RESPONSE_PROMPT,
    AI_ASSISTANT_NAME
)
from database import get_recent_messages_formatted

def _call_openai_api(prompt_text):
    payload = {
        "model": OPENAI_MODEL_NAME,
        "messages": [{"role": "system", "content": prompt_text}],
        "stream": False,
    }
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        response = requests.post(OPENAI_API_URL, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        logging.error(f"OpenAI API Error {response.status_code}: {response.text}")
        return f"Error: {response.status_code}."
    except requests.RequestException as e:
        logging.error(f"OpenAI API Request Failed: {e}")
        return "Error with OpenAI API request."

def generate_final_response(user_id, scraped_text, user_text):
    """
    Generate the final response for the user.
    """
    # Format the prompt
    final_prompt = FINAL_RESPONSE_PROMPT.format(
        ai_assistant_name=AI_ASSISTANT_NAME,
        previous_messages=get_recent_messages_formatted(user_id),
        scraped_text=scraped_text or "No additional content provided.",
        user_message=user_text
    )

    logging.debug(f"Final prompt generated: {final_prompt}")
    return _call_openai_api(final_prompt).strip()

def generate_wait_message(user_text):
    prompt = f"""\
You are a language expert. The user has just sent the following message:
\"{user_text}\"

Please produce exactly one short sentence that says something along the lines of:
"Please wait while I check the link..."
but in the same language the user wrote in. Keep it very short.
"""

    result = _call_openai_api(prompt)
    return result.strip()
