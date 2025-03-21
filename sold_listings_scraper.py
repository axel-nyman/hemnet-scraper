from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import logging
import os
import json
import re
from datetime import datetime
import locale

# Add this function to parse the Swedish date string
def parse_swedish_date(date_str):
    if not date_str:
        return None
    
    try:
        # Try to set Swedish locale for month name parsing
        try:
            # First try Swedish locale
            locale.setlocale(locale.LC_TIME, 'sv_SE.UTF-8')
        except locale.Error:
            try:
                # Fallback to Swedish locale with different format
                locale.setlocale(locale.LC_TIME, 'sv_SE')
            except locale.Error:
                # If neither works, we'll handle month mapping manually
                pass
                
        # Remove "Såld " prefix if present
        if date_str.startswith("Såld "):
            date_str = date_str[5:]
            
        # Try to parse with locale
        try:
            # Try to parse with day month year format
            return datetime.strptime(date_str, "%d %B %Y")
        except ValueError:
            # If locale parsing fails, manually map Swedish month names
            months = {
                'januari': 1, 'jan': 1,
                'februari': 2, 'feb': 2,
                'mars': 3, 'mar': 3,
                'april': 4, 'apr': 4,
                'maj': 5,
                'juni': 6, 'jun': 6,
                'juli': 7, 'jul': 7,
                'augusti': 8, 'aug': 8,
                'september': 9, 'sep': 9,
                'oktober': 10, 'okt': 10,
                'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            
            # Split the date string
            parts = date_str.split()
            if len(parts) == 3:
                day = int(parts[0])
                month_name = parts[1].lower()
                year = int(parts[2])
                
                if month_name in months:
                    return datetime(year, months[month_name], day)
    except Exception as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
    
    return None


# Configure logging
# Default to current directory for local development, but use /app/logs in Docker
log_directory = os.environ.get('LOG_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'))

try:
    os.makedirs(log_directory, exist_ok=True)
except OSError as e:
    print(f"Warning: Could not create log directory at {log_directory}: {e}")
    # Fall back to current working directory if we can't create the specified directory
    log_directory = os.getcwd()
    print(f"Falling back to current directory for logs: {log_directory}")
    os.makedirs(os.path.join(log_directory, 'logs'), exist_ok=True)
    log_directory = os.path.join(log_directory, 'logs')

log_filename = f"hemnet_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(log_directory, log_filename)

# Create logger
logger = logging.getLogger('hemnet_scraper')
logger.setLevel(logging.INFO)

# Create file handler
try:
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)
    
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Warning: Could not set up file logging: {e}")
    # We'll still have console logging

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

logger.info(f"Logging initialized. Log file: {log_path}")

BASE_URL_SOLD = "https://www.hemnet.se/salda/bostader?page="

def get_sold_listing_urls(page_number, browser):
    listings = list()
    url = BASE_URL_SOLD + str(page_number)
    logger.info(f"Fetching sold listings from page {page_number}: {url}")
    try:
        page = browser.new_page()
        page.goto(url)
        soup = BeautifulSoup(page.content(), 'html.parser')
        
        result_list = soup.find('div', attrs={'data-testid': 'result-list'})
        
        if not result_list:
            logger.warning(f"Result list not found on page {page_number}")
            page.close()
            return listings
        
        for link in result_list.find_all('a'):
            href = link.get('href')
            if href and href.startswith('/salda'):
                listings.append(href)
        
        logger.info(f"Found {len(listings)} sold listings on page {page_number}")
        page.close()
        return listings
    except Exception as e:
        logger.error(f"Error fetching sold listing URLs from page {page_number}: {e}")
        if 'page' in locals() and page:
            page.close()
        return []

def extract_hemnet_ids(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all <script> tags
    script_tags = soup.find_all("script")
    
    for script in script_tags:
        if script.string and 'saleId' in script.string:
            try:
                # Extract JSON content
                json_text = re.search(r'({.*})', script.string, re.DOTALL)
                if json_text:
                    data = json.loads(json_text.group(1))
                    
                    # Navigate to the relevant section
                    sale_id = data.get("props", {}).get("pageProps", {}).get("saleId")
                    listings = data.get("props", {}).get("pageProps", {}).get("__APOLLO_STATE__", {})
                    
                    original_listing_id = None
                    if sale_id and f"SoldPropertyListing:{sale_id}" in listings:
                        original_listing_id = listings[f"SoldPropertyListing:{sale_id}"].get("listingId")
                    
                    return sale_id, original_listing_id
            except json.JSONDecodeError:
                continue
    
    return None, None

def extract_listing_data_from_json(html_content):
    """Extract all listing data from the embedded JSON in the page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the Next.js data script
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    
    if not next_data_script or not next_data_script.string:
        return None, None, {}, False
    
    try:
        # Parse the JSON data
        data = json.loads(next_data_script.string)
        
        # Navigate to the relevant sections
        page_props = data.get("props", {}).get("pageProps", {})
        sale_id = page_props.get("saleId")
        
        # Get Apollo state which contains the listing data
        apollo_state = page_props.get("__APOLLO_STATE__", {})
        
        # Find the listing data using the sale ID
        listing_key = f"SoldPropertyListing:{sale_id}"
        
        if listing_key in apollo_state:
            listing_data = apollo_state[listing_key]
            original_listing_id = listing_data.get("listingId")
            sale_date_str = listing_data.get("formattedSoldAt", "")
            sale_date_datetime = parse_swedish_date(sale_date_str)
            
            # Extract using amount values instead of formatted values
            extracted_data = {
                "title": f"{listing_data.get('housingForm', {}).get('name', '')} {listing_data.get('formattedLivingArea', '')} - {listing_data.get('locationName', '')}",
                "final_price": listing_data.get("sellingPrice", {}).get("amount") if listing_data.get("sellingPrice") else None,
                "sale_date_str": sale_date_str,
                "sale_date": sale_date_datetime,
                "asking_price": listing_data.get("askingPrice", {}).get("amount") if listing_data.get("askingPrice") else None,
                "price_change": listing_data.get("priceChange", {}).get("amount") if listing_data.get("priceChange") else None,
                "price_change_percentage": listing_data.get("priceChangePercentage") if "priceChangePercentage" in listing_data else None,
                "living_area": listing_data.get("livingArea"),
                "land_area": listing_data.get("landArea"),
                "street_address": listing_data.get("streetAddress", ""),
                "area": listing_data.get("area", ""),
                "municipality": listing_data.get("municipality", {}).get("__ref", "").split(":")[-1] if listing_data.get("municipality") else "",
                "running_costs": listing_data.get("runningCosts", {}).get("amount") if listing_data.get("runningCosts") else None,
                "rooms": listing_data.get("numberOfRooms"),
                "construction_year": listing_data.get("legacyConstructionYear", ""),
                "broker_agency": apollo_state.get(listing_data.get("brokerAgency", {}).get("__ref", ""), {}).get("name", "") if listing_data.get("brokerAgency") else ""
            }
            
            return sale_id, original_listing_id, extracted_data, True
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON data: {e}")
    except Exception as e:
        logger.error(f"Error extracting data from JSON: {e}")
    
    return None, None, {}, False

def get_sold_listing_data(url, browser):
    logger.info(f"Fetching data for sold listing: {url}")
    try:
        page = browser.new_page()
        page.goto(url)
        html_content = page.content()
        
        # Try to extract data from JSON first
        sale_id, original_listing_id, json_data, success = extract_listing_data_from_json(html_content)
        
        if success and json_data:
            json_data["sale_hemnet_id"] = sale_id
            json_data["original_hemnet_id"] = original_listing_id
            json_data["url"] = url
            
            logger.info(f"Successfully extracted JSON data for sold listing {sale_id}")
            page.close()
            return json_data
        
        # If JSON extraction fails, fall back to the old method
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract sale ID and original listing ID
        sale_id, original_listing_id = extract_hemnet_ids(html_content)
        
        if not sale_id:
            logger.warning(f"Sale ID not found for {url}")
            # Fall back to extracting ID from URL
            sale_id = url.split('-')[-1] if '-' in url else None
        
        if not original_listing_id:
            logger.warning(f"Original listing ID not found for {url}")
        
        # Try to extract data from JSON-LD if available
        json_ld_script = soup.find("script", type="application/ld+json")
        if json_ld_script:
            try:
                json_ld = json.loads(json_ld_script.string)
                title = json_ld.get("name", "")
                final_price = json_ld.get("offers", {}).get("price", "")
                sale_date = json_ld.get("dateSold", "")
            except:
                title = ""
                final_price = ""
                sale_date = ""
        else:
            # Last resort: Try to find the data in the HTML
            title = soup.find("h1").text.strip() if soup.find("h1") else ""
            
            # Try different selector patterns for the price
            price_element = (
                soup.find("span", class_=lambda c: c and "sellingPriceText" in c) or
                soup.find("div", class_=lambda c: c and "PriceDetails" in c) or
                soup.find("p", class_=lambda c: c and "Price" in c)
            )
            final_price = price_element.text.strip() if price_element else ""
            
            # Try different selector patterns for the sale date
            date_element = (
                soup.find("p", class_=lambda c: c and "hclText" in c) or
                soup.find("span", class_=lambda c: c and "SoldDate" in c) or
                soup.find("div", class_=lambda c: c and "Date" in c)
            )
            sale_date_str = date_element.text.strip() if date_element else ""
            sale_date_datetime = parse_swedish_date(sale_date_str)
        
        data = {
            "title": title,
            "final_price": final_price,
            "sale_date_str": sale_date_str,
            "sale_date": sale_date_datetime,
            "sale_hemnet_id": sale_id,
            "original_hemnet_id": original_listing_id,
            "url": url
        }
        
        logger.debug(f"Extracted data for sold listing {sale_id} with fallback method")
        page.close()
        return data
    except Exception as e:
        logger.error(f"Error processing sold listing {url}: {e}")
        if 'page' in locals() and page:
            page.close()
        return {}

def store_sold_listing(data):
    # Placeholder function for future database implementation
    pass

def scrape_sold_listings():
    try:
        logger.info("Starting browser session for sold listings")
        with sync_playwright() as p:
            browser = p.webkit.launch(headless=True)
            
            try:
                for page in range(1, 51):  # Scrape up to 50 pages
                    urls = get_sold_listing_urls(page, browser)
                    logger.info(f"Processing {len(urls)} sold listings from page {page}")
                    
                    for url in urls:
                        try:
                            data = get_sold_listing_data("https://www.hemnet.se" + url, browser)
                            if data:
                                store_sold_listing(data)  # Store in database later
                        except Exception as e:
                            logger.error(f"Error processing individual sold listing {url}: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error in main page processing loop: {e}")
            
            logger.info("Closing browser session")
            browser.close()
    except Exception as e:
        logger.critical(f"Critical error in sold listings scraper: {e}")
    finally:
        logger.info("Scraping complete.")

if __name__ == "__main__":
    scrape_sold_listings()