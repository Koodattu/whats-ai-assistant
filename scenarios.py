from pydantic import BaseModel
from prompts import BASE_FINAL_RESPONSE_PROMPT, HAIRDRESSER_FINAL_RESPONSE_PROMPT, CAR_PARTS_RETAILER_FINAL_RESPONSE_PROMPT, BOOKSTORE_FINAL_RESPONSE_PROMPT
import openai

class GenerateImageTool(BaseModel):
    prompt: str

class EditImageTool(BaseModel):
    prompt: str

class GenerateTTSTool(BaseModel):
    text: str

class WebSearchTool(BaseModel):
    query: str

class Scenario:
    name = "base"
    final_response_prompt = BASE_FINAL_RESPONSE_PROMPT
    tools = [
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

class CheckAppointmentCalendarTool(BaseModel):
    start_date: str
    end_date: str

class GetServicesTool(BaseModel):
    gender: str

class GetOrderHistoryTool(BaseModel):
    phone_number: str

class BookAppointmentTool(BaseModel):
    phone_number: str
    service: str
    preferred_time: str

class CancelAppointmentTool(BaseModel):
    phone_number: str

class HairdresserScenario(Scenario):
    name = "hairdresser"
    final_response_prompt = HAIRDRESSER_FINAL_RESPONSE_PROMPT
    tools = [
        openai.pydantic_function_tool(
            CheckAppointmentCalendarTool,
            name="check_appointment_calendar_tool",
            description="Check the appointment calendar for a date range. Provide start and end dates.",
        ),
        openai.pydantic_function_tool(
            GetServicesTool,
            name="get_services_tool",
            description="Get available services based on the user's gender.",
        ),
        openai.pydantic_function_tool(
            GetOrderHistoryTool,
            name="get_order_history_tool",
            description="Get the user's order history by their phone number.",
        ),
        openai.pydantic_function_tool(
            BookAppointmentTool,
            name="book_appointment_tool",
            description="Book an appointment for a service at a preferred time. Provide the user's phone number, service, and preferred time.",
        ),
        openai.pydantic_function_tool(
            CancelAppointmentTool,
            name="cancel_appointment_tool",
            description="Cancel an appointment by the user's phone number.",
        ),
    ]

class FindCarInfoWithPlateTool(BaseModel):
    license_plate: str

class FindCompatiblePartTool(BaseModel):
    license_plate: str
    part_type: str

class PlaceCarPartOrderTool(BaseModel):
    phone_number: str
    part_id: str
    quantity: int

class CheckCarPartOrderTool(BaseModel):
    phone_number: str

class CarPartsRetailerScenario(Scenario):
    name = "car_parts_retailer"
    final_response_prompt = CAR_PARTS_RETAILER_FINAL_RESPONSE_PROMPT
    tools = [
        openai.pydantic_function_tool(
            FindCarInfoWithPlateTool,
            name="find_car_info_with_plate_tool",
            description="Find car information using the license plate number."
        ),
        openai.pydantic_function_tool(
            FindCompatiblePartTool,
            name="find_compatible_part_tool",
            description="Find compatible car parts based on the license plate and part type."
        ),
        openai.pydantic_function_tool(
            PlaceCarPartOrderTool,
            name="place_car_part_order_tool",
            description="Place an order for a car part. Requires the user's phone number, part ID, and quantity."
        ),
        openai.pydantic_function_tool(
            CheckCarPartOrderTool,
            name="check_car_part_order_tool",
            description="Check the status of a car part order by the user's phone number."
        ),
    ]

class ViewBookOrderHistoryTool(BaseModel):
    phone_number: str

class SuggestBooksTool(BaseModel):
    genre: str = None
    author: str = None

class CheckBookStockTool(BaseModel):
    title: str
    author: str = None

class ReserveBookTool(BaseModel):
    phone_number: str
    title: str

class CancelBookTool(BaseModel):
    phone_number: str
    title: str

class BookstoreScenario(Scenario):
    name = "bookstore"
    final_response_prompt = BOOKSTORE_FINAL_RESPONSE_PROMPT
    tools = [
        openai.pydantic_function_tool(
            ViewBookOrderHistoryTool,
            name="view_book_order_history_tool",
            description="View the user's book order history by their phone number."
        ),
        openai.pydantic_function_tool(
            SuggestBooksTool,
            name="suggest_books_tool",
            description="Suggest books based on genre or author. If both are provided, prioritize genre.",
        ),
        openai.pydantic_function_tool(
            CheckBookStockTool,
            name="check_book_stock_tool",
            description="Check if a book is in stock by title and optionally author.",
        ),
        openai.pydantic_function_tool(
            ReserveBookTool,
            name="reserve_book_tool",
            description="Reserve a book for the user. Requires phone number and book title.",
        ),
        openai.pydantic_function_tool(
            CancelBookTool,
            name="cancel_book_tool",
            description="Cancel a book reservation by the user's phone number and book title.",
        ),
    ]

SCENARIOS = {
    "base": Scenario(),
    "hairdresser": HairdresserScenario(),
    "car_parts_retailer": CarPartsRetailerScenario(),
    "bookstore": BookstoreScenario(),
}