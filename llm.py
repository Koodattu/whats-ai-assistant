# llm.py
import requests
import json
import logging
from config import (
    LLM_PROVIDER, OPENAI_API_KEY,
    OLLAMA_API_URL, OLLAMA_MODEL_NAME, 
    OPENAI_API_URL, OPENAI_MODEL_NAME,
    SUMMARIZE_PROMPT_EN, SUMMARIZE_PROMPT_FI,
    FINAL_RESPONSE_PROMPT_EN, FINAL_RESPONSE_PROMPT_FI,
    LANG_SELECTED, MAX_MESSAGES, AI_ASSISTANT_NAME
)
from database import get_recent_messages

def _call_llm_api(prompt_text):
    print(f"Calling LLM with prompt: {prompt_text}")
    if LLM_PROVIDER == "openai":
        return _call_openai_api(prompt_text)
    return _call_local_llm_api(prompt_text)

def _call_local_llm_api(prompt_text):
    payload = {"model": OLLAMA_MODEL_NAME, "prompt": prompt_text, "stream": False}
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(OLLAMA_API_URL, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "No response from local model.").strip()
        logging.error(f"Local LLM Error {response.status_code}: {response.text}")
        return f"Error: {response.status_code}."
    except requests.RequestException as e:
        logging.error(f"Local LLM Request Failed: {e}")
        return "Error with local LLM request."

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

def generate_first_time_greeting(user_name, user_message):
    greeting_prompt = f"""\
You are {AI_ASSISTANT_NAME}, a friendly artificial intelligence assistant.
This is your first interaction with the user.
The user has just sent the following message:
"{user_message}"

Please greet the user by their name "{user_name}".
Respond in the same language as the user's message.
Keep the greeting short and welcoming.
Tell the user your name and that you are an AI assistant.
IMPORTANT: Only greet the user, tell your name and the fact that you are an artificial intelligence assistant.
"""
    return _call_llm_api(greeting_prompt).strip()

def summarize_conversation(user_id):
    """
    Summarize the most recent messages for the user into a concise format.
    """
    # Retrieve the most recent messages
    conversation_history = get_recent_messages(user_id, MAX_MESSAGES)

    # Build a minimal text representation of the conversation
    lines = []
    for msg_content, msg_timestamp, from_me in conversation_history:
        if from_me:
            speaker = "ME"
        else:
            speaker = "USER"
        lines.append(f"{speaker}: {msg_content}")

    conversation_text = "\n".join(lines)

    # Choose prompt template based on language
    if LANG_SELECTED == "FI":
        prompt_template = SUMMARIZE_PROMPT_FI
    else:
        prompt_template = SUMMARIZE_PROMPT_EN

    # Format the prompt
    prompt = prompt_template.format(conversation=conversation_text)

    return _call_llm_api(prompt).strip()

def generate_final_response(conversation_summary, scraped_text, user_text):
    """
    Generate the final response for the user.
    """
    # Choose prompt template based on language
    if LANG_SELECTED == "FI":
        prompt_template = FINAL_RESPONSE_PROMPT_FI
    else:
        prompt_template = FINAL_RESPONSE_PROMPT_EN

    # Format the prompt
    final_prompt = prompt_template.format(
        ai_assistant_name=AI_ASSISTANT_NAME,
        conversation_summary=conversation_summary,
        scraped_text=scraped_text or "No additional content provided.",
        user_message=user_text
    )

    return _call_llm_api(final_prompt).strip()

def generate_wait_message(user_text):
    prompt = f"""\
You are a language expert. The user has just sent the following message:
\"{user_text}\"

Please produce exactly one short sentence that says something along the lines of:
"Please wait while I check the link..."
but in the same language the user wrote in. Keep it very short.
"""

    result = _call_llm_api(prompt)
    return result.strip()
