import logging
from database import get_recent_messages_formatted
from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL_NAME,
    AI_ASSISTANT_NAME
)
import openai
from openai.types.chat import ChatCompletion

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def _call_openai_api(system_prompt, user_message):
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        completion: ChatCompletion = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=messages,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI API Request Failed: {e}")
        return "Error with OpenAI API request."

def generate_final_response(prompt_base, user_id, scraped_text, user_text, tool_usage_result):
    """
    Generate the final response for the user.
    """
    # Format the prompt
    final_prompt = prompt_base.format(
        ai_assistant_name=AI_ASSISTANT_NAME,
        previous_messages=get_recent_messages_formatted(user_id),
        scraped_text=scraped_text or "No additional content provided.",
        tool_usage_result=tool_usage_result or "No tools were used.",
    )

    logging.debug(f"Final prompt generated: {final_prompt}")
    return _call_openai_api(final_prompt, user_text).strip()

def generate_wait_message(user_text=None, user_id=None):
    if user_text is None:
        user_text = get_recent_messages_formatted(user_id=user_id)
    prompt = """Please produce exactly one short sentence that says something along the lines of: \"Please wait, just one moment\" but in the same language the user wrote in. Keep it very short."""
    return _call_openai_api(prompt, user_text).strip()

def generate_error_message(user_text=None, user_id=None):
    if user_text is None:
        user_text = get_recent_messages_formatted(user_id=user_id)
    prompt = """Please produce exactly one short sentence that says something along the lines of: \"An error occurred, please try again later\" but in the same language the user wrote in. Keep it very short."""
    return _call_openai_api(prompt, user_text).strip()

