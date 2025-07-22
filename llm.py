import logging
from config import (
    OPENAI_API_KEY,
    OPENAI_MODEL_NAME,
    FINAL_RESPONSE_PROMPT,
    AI_ASSISTANT_NAME
)
from database import get_recent_messages_formatted
import base64
import mimetypes
import os
import openai
from enum import Enum
from pydantic import BaseModel

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def _call_openai_api(prompt_text):
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL_NAME,
            messages=[{"role": "system", "content": prompt_text}],
            stream=False,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
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
The user has just sent the following message: \"{user_text}\"
Please produce exactly one short sentence that says something along the lines of:
\"Please wait, just one moment\"
but in the same language the user wrote in.
Keep it very short.
"""
    result = _call_openai_api(prompt)
    return result.strip()

class GenerateImageTool(BaseModel):
    prompt: str

class EditTarget(str, Enum):
    current = "current"
    previous = "previous"

class EditImageTool(BaseModel):
    prompt: str
    edit_target: EditTarget

class GenerateTTSTool(BaseModel):
    text: str

available_tools = [
    openai.pydantic_function_tool(
        GenerateImageTool,
        name="generate_image_tool",
        description="Generate a new image from a user prompt using GPT-image-1. Only provide the prompt."
    ),
    openai.pydantic_function_tool(
        EditImageTool,
        name="edit_image_tool",
        description="Edit the current or previous image using a user prompt. Only provide the prompt and specify whether to edit the current or previous image."
    ),
    openai.pydantic_function_tool(
        GenerateTTSTool,
        name="generate_tts_tool",
        description="Generate speech audio from a user prompt. Only provide the text to be spoken."
    ),
]

def poll_llm_for_tool_choice(user_message, system_prompt=None, model="gpt-4o"):
    """
    Poll the LLM to decide which tool to call for a user request.
    Returns the tool call(s) and arguments if any.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    try:
        completion = client.chat.completions.parse(
            model=model,
            messages=messages,
            tools=available_tools,
        )
        tool_calls = completion.choices[0].message.tool_calls or []
        return tool_calls
    except Exception as e:
        logging.error(f"Tool polling LLM failed: {e}")
        return []

def text_to_speech_with_openai(text, model="gpt-4o-mini-tts", voice="alloy", response_format="wav"):
    """
    Generate speech audio from text using OpenAI's TTS API.
    Returns the audio bytes (e.g., MP3).
    """
    try:
        response = client.audio.speech.create(
            model=model,
            input=text,
            voice=voice,
            response_format=response_format,
        )
        return response.content
    except Exception as e:
        logging.error(f"OpenAI TTS API Request Failed: {e}")
        return None

def generate_image_with_openai(prompt, model="dall-e-3", size="1024x1024", response_format="b64_json"):
    """
    Generate an image from a prompt using OpenAI's image API (DALL-E).
    Returns base64 string if response_format is 'b64_json'.
    """
    try:
        response = client.images.generate(
            prompt=prompt,
            model=model,
            size=size,
            response_format=response_format,
            quality="standard",
            n=1,
        )
        # Return base64 string or URL depending on response_format
        if response_format == "b64_json":
            return response.data[0].b64_json
        else:
            return response.data[0].url
    except Exception as e:
        logging.error(f"OpenAI Image Generation Failed: {e}")
        return None


def edit_image_with_openai(image_path, prompt, model="dall-e-3", size="1024x1024", response_format="b64_json"):
    """
    Edit an image using OpenAI's image API (DALL-E).
    Requires an input image file path and a prompt.
    Returns base64 string if response_format is 'b64_json'.
    """
    try:
        with open(image_path, "rb") as image_file:
            response = client.images.edit(
                image=image_file,
                prompt=prompt,
                model=model,
                size=size,
                response_format=response_format,
                n=1,
            )
        if response_format == "b64_json":
            return response.data[0].b64_json
        else:
            return response.data[0].url
    except Exception as e:
        logging.error(f"OpenAI Image Editing Failed: {e}")
        return None

def describe_image_with_gpt(image_path_or_url, prompt_text="Describe the image.", detail="low"):
    """
    Describe an image using OpenAI's GPT-4o Vision API via openai-python.
    Accepts a local image file path or an image URL.
    """
    # Determine if input is a file path or URL
    if os.path.isfile(image_path_or_url):
        mime_type, _ = mimetypes.guess_type(image_path_or_url)
        if not mime_type:
            mime_type = "image/jpeg"
        with open(image_path_or_url, "rb") as img_file:
            b64_image = base64.b64encode(img_file.read()).decode("utf-8")
        image_url = f"data:{mime_type};base64,{b64_image}"
    else:
        image_url = image_path_or_url

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": detail}},
                    ],
                }
            ],
            max_tokens=300,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI Vision API Request Failed: {e}")
        return "Error with OpenAI Vision API request."



def transcribe_audio_with_whisper(audio_file_path, prompt=None):
    """
    Transcribe an audio file using OpenAI Whisper API via openai-python.
    Accepts a local audio file path. Optionally, a prompt for better accuracy.
    """
    try:
        with open(audio_file_path, "rb") as audio_file:
            params = {"model": "whisper-1", "file": audio_file}
            if prompt:
                params["prompt"] = prompt
            transcription = client.audio.transcriptions.create(**params)
        # The response object has a .text attribute
        return getattr(transcription, "text", None) or transcription
    except Exception as e:
        logging.error(f"OpenAI Whisper API Request Failed: {e}")
        return "Error with OpenAI Whisper API request."
