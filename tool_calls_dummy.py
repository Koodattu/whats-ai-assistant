def dummy_check_appointment_calendar_tool(start_date: str, end_date: str):
    return {
        "available_slots": [
            {"date": start_date, "times": ["09:00", "11:00", "15:00"]},
            {"date": end_date, "times": ["10:00", "14:00", "16:00"]}
        ],
        "message": f"Available slots between {start_date} and {end_date}."
    }

def dummy_get_services_tool(gender: str):
    return {
        "gender": gender,
        "services": [
            {"name": "Haircut", "duration_minutes": 30, "price_eur": 25},
            {"name": "Coloring", "duration_minutes": 60, "price_eur": 60},
            {"name": "Styling", "duration_minutes": 45, "price_eur": 35}
        ] if gender.lower() == "female" else [
            {"name": "Haircut", "duration_minutes": 20, "price_eur": 20},
            {"name": "Shaving", "duration_minutes": 15, "price_eur": 15}
        ]
    }

def dummy_get_order_history_tool(phone_number: str):
    return {
        "phone_number": phone_number,
        "history": [
            {"date": "2025-06-01", "service": "Haircut", "price_eur": 25, "status": "completed"},
            {"date": "2025-05-15", "service": "Coloring", "price_eur": 60, "status": "completed"}
        ]
    }

def dummy_book_appointment_tool(phone_number: str, service: str, preferred_time: str):
    return {
        "phone_number": phone_number,
        "service": service,
        "preferred_time": preferred_time,
        "confirmation_number": "HAIR123456",
        "status": "booked",
        "message": f"Appointment for {service} booked at {preferred_time}."
    }

def dummy_cancel_appointment_tool(phone_number: str):
    return {
        "phone_number": phone_number,
        "status": "cancelled",
        "message": "Your appointment has been cancelled."
    }

# --- Dummy Tool Implementations for Car Parts Retailer Scenario ---

def dummy_find_car_info_with_plate_tool(license_plate: str):
    return {
        "license_plate": license_plate,
        "car": {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2018,
            "color": "Blue",
            "vin": "JT123456789012345"
        }
    }

def dummy_find_compatible_part_tool(license_plate: str, part_type: str):
    return {
        "license_plate": license_plate,
        "part_type": part_type,
        "compatible_parts": [
            {"part_id": "CP-001", "name": f"{part_type} Premium", "price_eur": 120, "in_stock": True},
            {"part_id": "CP-002", "name": f"{part_type} Standard", "price_eur": 80, "in_stock": False}
        ]
    }

def dummy_place_car_part_order_tool(phone_number: str, part_id: str, quantity: int):
    return {
        "order_id": "ORDER987654",
        "phone_number": phone_number,
        "part_id": part_id,
        "quantity": quantity,
        "status": "placed",
        "estimated_delivery": "2025-07-30"
    }

def dummy_check_car_part_order_tool(phone_number: str):
    return {
        "phone_number": phone_number,
        "orders": [
            {
                "order_id": "ORDER987654",
                "part_id": "CP-001",
                "status": "shipped",
                "shipped_date": "2025-07-25",
                "estimated_delivery": "2025-07-30"
            }
        ]
    }

# --- Dummy Tool Implementations for Bookstore Scenario ---

def dummy_view_book_order_history_tool(phone_number: str):
    return {
        "phone_number": phone_number,
        "orders": [
            {"title": "1984", "author": "George Orwell", "date": "2025-06-10", "status": "delivered"},
            {"title": "Brave New World", "author": "Aldous Huxley", "date": "2025-05-20", "status": "delivered"}
        ]
    }

def dummy_suggest_books_tool(genre: str = None, author: str = None):
    suggestions = []
    if genre:
        suggestions.append({"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": genre})
        suggestions.append({"title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": genre})
    elif author:
        suggestions.append({"title": "Book by " + author, "author": author, "genre": "Fiction"})
    else:
        suggestions.append({"title": "Random Book", "author": "Random Author", "genre": "General"})
    return {
        "genre": genre,
        "author": author,
        "suggestions": suggestions
    }

def dummy_check_book_stock_tool(title: str, author: str = None):
    return {
        "title": title,
        "author": author,
        "in_stock": True,
        "stock_count": 7,
        "location": "Aisle 3, Shelf B"
    }

def dummy_reserve_book_tool(phone_number: str, title: str):
    return {
        "phone_number": phone_number,
        "title": title,
        "reservation_id": "RES123456",
        "status": "reserved",
        "pickup_deadline": "2025-08-01"
    }

def dummy_cancel_book_tool(phone_number: str, title: str):
    return {
        "phone_number": phone_number,
        "title": title,
        "status": "cancelled",
        "message": f"Reservation for '{title}' has been cancelled."
    }