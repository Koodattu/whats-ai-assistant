import os
from config import (
    LLM_PROVIDER,
    AI_ASSISTANT_NAME,
    AZURE_SUBSCRIPTION_KEY,
    AZURE_ENDPOINT,
    AZURE_DEPLOYMENT_NAME,
    AZURE_API_VERSION
)
from prompts import (
    GREETING_PROMPT, FINAL_RESPONSE_PROMPT
)
from database import get_recent_messages_formatted
from openai import AzureOpenAI

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
            max_tokens=100,
        )
        # Correctly access the response content
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return ""

def generate_first_time_greeting(user_name, user_message, custom_prompt):
    """
    Generate the first-time greeting for the user.
    """
    # Call the LLM API with the prompt containing the placeholder.
    system_prompt = (custom_prompt + "\n" + GREETING_PROMPT).format(ai_assistant_name=AI_ASSISTANT_NAME)
    raw_response = call_llm_api(system_prompt, user_message)
    # Replace the placeholder with the actual user name before sending the message.
    final_response = raw_response.replace("USER_NAME_HERE", user_name)
    return final_response

def generate_final_response(user_id, user_text, custom_prompt):
    """
    Generate the final response for the user.
    """
    # read all contents from all text files inside converted folder
    conversation_history = get_recent_messages_formatted(user_id)
    additional_content = ""
    for file in os.listdir("converted"):
        with open(os.path.join("converted", file), "r", encoding="utf-8", errors="replace") as f:
            additional_content += f.read()
    system_prompt = (custom_prompt + "\n" + FINAL_RESPONSE_PROMPT).format(
        ai_assistant_name=AI_ASSISTANT_NAME,
        previous_messages=conversation_history,
        additional_content=additional_content or "No additional content provided.",
    )
    return call_llm_api(system_prompt, user_text)
