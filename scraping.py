# scraping.py
import requests
from bs4 import BeautifulSoup

def scrape_text(url):
    """
    Fetches the URL and returns the raw text.
    If the site is 'nettimokki', it also includes the full characteristic list HTML.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()  # Raise error if not 200
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all text
        text = soup.get_text(separator="\n")
        # Optionally do some cleanup
        text = " ".join(text.split())

        # Check if the URL belongs to 'nettimokki'
        if "nettimokki" in url:
            characteristic_list = soup.find("ul", class_="characteristic-list")
            
            if characteristic_list:
                text += f"\n\nCharacteristics List:\n{str(characteristic_list)}"
            
            text = text + "\n\n(NOTE: block-icon means NO and check-icon means YES))"
        
        return text
    except Exception as e:
        return f"Could not scrape the link: {e}"