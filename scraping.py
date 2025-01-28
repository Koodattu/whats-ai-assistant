# scraping.py
import requests
from bs4 import BeautifulSoup

def scrape_text(url):
    """
    Fetches the URL and returns the raw text.
    You can make this as fancy as needed: handle PDFs, handle images, 
    or parse out certain sections, etc.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()  # Raise error if not 200
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all text
        text = soup.get_text(separator="\n")
        # Optionally do some cleanup
        text = " ".join(text.split())
        #text = text[:2000]
        return text
    except Exception as e:
        return f"Could not scrape the link: {e}"
