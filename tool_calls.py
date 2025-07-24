import random
import base64
import mimetypes
import os
from enum import Enum
from pydantic import BaseModel
from PIL import Image
import io
from config import (
    OPENAI_MODEL_NAME,
    OPENAI_API_KEY
)
import openai
from openai.types.chat import ParsedFunctionToolCall
import logging
import requests
from scraping import scrape_text
from ddgs import DDGS
from filelogger import FileLogger
fileLogger = FileLogger()

client = openai.OpenAI(api_key=OPENAI_API_KEY)

class GenerateImageTool(BaseModel):
    prompt: str

class EditImageTool(BaseModel):
    prompt: str

class GenerateTTSTool(BaseModel):
    text: str

class WebSearchTool(BaseModel):
    query: str

available_tools = [
    openai.pydantic_function_tool(
        GenerateImageTool,
        name="generate_image_tool",
        description="Generate a new image from a user prompt. Only provide the prompt."
    ),
    openai.pydantic_function_tool(
        EditImageTool,
        name="edit_image_tool",
        description="Edit the latest image using a user prompt. Only provide the prompt how the image should be edited."
    ),
    openai.pydantic_function_tool(
        GenerateTTSTool,
        name="generate_tts_tool",
        description="Generate speech audio from text. Only provide the text to be spoken. This should be used when the user request audio output.",
    ),
    openai.pydantic_function_tool(
        WebSearchTool,
        name="web_search_tool",
        description="Search the web for up-to-date information. Only provide the search query."
    ),
]

def poll_llm_for_tool_choice(user_message) -> ParsedFunctionToolCall | None:
    """
    Poll the LLM to decide which tool to call for a user request.
    Returns the tool call(s) and arguments if any.
    """
    messages = []
    system_prompt = "Select zero or one tool to call based on the user message. We don't want to call tools for every user message, only when necessary. If you don't need to call a tool, just return an empty list."
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})
    try:
        completion = client.beta.chat.completions.parse(
            model=OPENAI_MODEL_NAME,
            messages=messages,
            tools=available_tools,
        )
        fileLogger.log(f"[POLL_LLM_FOR_TOOL_CHOICE] [COMPLETION]: {str(completion)}")
        tool_call = completion.choices[0].message.tool_calls[0] or None
        fileLogger.log(f"[POLL_LLM_FOR_TOOL_CHOICE] [TOOL_CALLS]: {str(tool_call)}")
        return tool_call
    except Exception as e:
        logging.error(f"Tool polling LLM failed: {e}")
        return None

def text_to_speech_with_openai(text):
    """
    Generate speech audio from text using OpenAI's TTS API.
    Returns the audio file path.
    """
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            input=text,
            voice="alloy",
            response_format="mp3",
        )
        filename = f"tts_output_{random.randint(1, 9999999)}.mp3"
        filepath = os.path.join("audio", filename)
        with open(filepath, "wb") as audio_file:
            audio_file.write(response.content)
        logging.info(f"Audio saved to {filepath}")
        return filepath
    except Exception as e:
        logging.error(f"OpenAI TTS API Request Failed: {e}")
        return None

def generate_image_with_openai(prompt):
    """
    Generate an image from a prompt using OpenAI's image API (GPT-Image-1).
    """
    try:
        response = client.images.generate(
            prompt=prompt,
            model="gpt-image-1",
            quality="medium",
            n=1
        )
        image_data = base64.b64decode(response.data[0].b64_json)
        image = Image.open(io.BytesIO(image_data))
        filename = f"gptimage1_generated_{random.randint(1, 9999999)}.png"
        filepath = os.path.join("images", filename)
        image.save(filepath)
        return filepath
    except Exception as e:
        logging.error(f"OpenAI Image Generation Failed: {e}")
        return None


def edit_image_with_openai(image_path, prompt):
    """
    Edit an image using OpenAI's image API (GPT-Image-1).
    Requires an input image file path and a prompt.
    """
    try:
        with open(image_path, "rb") as image_file:
            response = client.images.edit(
                image=image_file,
                prompt=prompt,
                model="gpt-image-1",
                quality="medium",
                n=1
            )
        image_data = base64.b64decode(response.data[0].b64_json)
        image = Image.open(io.BytesIO(image_data))
        filename = f"gptimage1_edited_{random.randint(1, 9999999)}.png"
        filepath = os.path.join("images", filename)
        image.save(filepath)
        return filepath
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
        with open(image_path_or_url, "rb") as img_file:
            b64_image = base64.b64encode(img_file.read()).decode("utf-8")
        image_url = f"data:{mime_type};base64,{b64_image}"

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

def transcribe_audio_with_whisper(audio_file_path):
    """
    Transcribe an audio file using OpenAI Whisper API via openai-python.
    Accepts a local audio file path. Optionally, a prompt for better accuracy.
    """
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcription.text.strip()
    except Exception as e:
        logging.error(f"OpenAI Whisper API Request Failed: {e}")
        return "Error with OpenAI Whisper API request."

def web_search(query):
    """
    Run a web search using DDGS and scrape the top N websites for content.
    """
    try:
        ddgs = DDGS().text(query, max_results=3, backend="duckduckgo")
        fileLogger.log(f"[WEB_SEARCH] [DDGS RESULTS]: {str(ddgs)}")
        results = []
        for result in ddgs:
            try:
                text = scrape_text(result['href'])
                results.append({"url": result['href'], "snippet": text})
            except Exception as e:
                results.append({"url": result['href'], "snippet": f"Failed to scrape: {e}"})
        fileLogger.log(f"[WEB_SEARCH] [RESULTS]: {str(results)}")
        return results
    except Exception as e:
        return [{"error": f"Web search failed: {e}"}]