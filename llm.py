import os
from config import (
    LLM_PROVIDER,
    AI_ASSISTANT_NAME,
    AZURE_SUBSCRIPTION_KEY,
    AZURE_ENDPOINT,
    AZURE_DEPLOYMENT_NAME,
    AZURE_API_VERSION
)
from database import get_recent_messages_formatted
from openai import AzureOpenAI
from pydantic import BaseModel
from neonize.utils import log

def get_client_and_model():
    """
    Returns an LLM client configured for the chosen provider.
    This example uses the OpenAI Python SDK interface for all providers.
    """
    if LLM_PROVIDER == "azure":
        return AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=AZURE_SUBSCRIPTION_KEY,
            api_version=AZURE_API_VERSION
        ), AZURE_DEPLOYMENT_NAME
    else:
        raise ValueError("Unsupported LLM Provider")

def call_llm_api(system_prompt, user_prompt):
    """
    Unified function to call the LLM API using the OpenAI Python SDK.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        # Call the chat completions endpoint using the client
        client, model = get_client_and_model()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500,
        )
        # Correctly access the response content
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return ""

class WatchdogResponse(BaseModel):
    relevant: bool

def call_watchdog_llm(user_message, watchdog_prompt):
    """
    Calls the watchdog LLM and returns True if the message is relevant, otherwise False.
    Uses a Pydantic model and the response_format parameter to ensure JSON format.
    """
    print("Calling watchdog LLM with user message:", user_message)
    additional_content = ""
    for file in os.listdir("converted"):
        with open(os.path.join("converted", file), "r", encoding="utf-8", errors="replace") as f:
            additional_content += f.read()
    system_prompt = watchdog_prompt.format(
        user_message=user_message,
        additional_content=additional_content or "Ei lisätietoa tiedostoista."
    )
    try:
        client, model = get_client_and_model()
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=10,
            response_format=WatchdogResponse
        )
        result = response.choices[0].message.parsed.relevant
        return bool(result)
    except Exception as e:
        print(f"Error calling watchdog LLM: {e}")
        log.exception(e)
        return False

def generate_first_time_greeting(user_name, user_message, public_prompt, private_prompt):
    """
    Luo ensimmäisen tervehdyksen yhdistämällä julkinen ja yksityinen prompti.
    """
    log.info(f"Generating first time greeting for user: {user_name}")
    system_prompt = (public_prompt + "\n" + private_prompt).format(ai_assistant_name=AI_ASSISTANT_NAME)
    raw_response = call_llm_api(system_prompt, user_message)
    final_response = raw_response.replace("USER_NAME_HERE", user_name)
    return final_response

def generate_final_response(user_id, user_text, public_prompt, private_prompt):
    """
    Luo loppuvastaus yhdistämällä julkinen ja yksityinen prompti.
    """
    conversation_history = get_recent_messages_formatted(user_id)
    additional_content = ""
    for file in os.listdir("converted"):
        with open(os.path.join("converted", file), "r", encoding="utf-8", errors="replace") as f:
            additional_content += f.read()
    system_prompt = (public_prompt + "\n" + private_prompt).format(
        ai_assistant_name=AI_ASSISTANT_NAME,
        previous_messages=conversation_history,
        additional_content=additional_content or "Ei lisätietoa tiedostoista.",
    )
    return call_llm_api(system_prompt, user_text)
