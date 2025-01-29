# scraping.py
import requests
from bs4 import BeautifulSoup

def scrape_text(url):
    """
    Fetches the URL and replaces occurrences of characteristic items
    in the text with formatted availability statements.
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
                for li in characteristic_list.find_all("li"):
                    feature_name = li.get_text(strip=True)
                    if "block-icon" in li.get("class", []):
                        replacement_text = f"{feature_name}: Ei\n"
                    elif "check-icon" in li.get("class", []):
                        replacement_text = f"{feature_name}: Kyllä\n"
                    else:
                        continue
                    
                    text = text.replace(feature_name, replacement_text)
        
        return text
    except Exception as e:
        return f"Could not scrape the link: {e}"