import gc
from bs4 import BeautifulSoup, SoupStrainer
import json
from datetime import datetime
import locale
from utils.logging_setup import setup_logging
from utils.playwright_utils import browser_context, page_context
from utils.database_utils import store_sold_listing

logger = setup_logging()

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

BASE_URL_SOLD = "https://www.hemnet.se/salda/bostader?page="

def get_sold_listing_urls(page_number, browser):
    url = f"https://www.hemnet.se/salda/bostader?page={page_number}"
    logger.info(f"Fetching sold listings from page {page_number}: {url}")
    
    with page_context(browser) as page:
        try:
            page.goto(url, wait_until="domcontentloaded")            
            parse_only = SoupStrainer('div', attrs={'data-testid': 'result-list'})
            soup = BeautifulSoup(page.content(), 'html.parser', parse_only=parse_only)
            
            if not soup:
                logger.warning(f"Result list not found on page {page_number}")
                return
            
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and href.startswith('/salda'):
                    yield href
                    
        except Exception as e:
            logger.error(f"Error fetching sold listing URLs from page {page_number}: {e}")

def extract_listing_data_from_json(html_content):
    """Extract listing data with minimal memory usage"""
    # Only parse the script tag we need
    parse_only = SoupStrainer('script', id='__NEXT_DATA__')
    soup = BeautifulSoup(html_content, 'html.parser', parse_only=parse_only)
    
    next_data_script = soup.find()
    if not next_data_script or not next_data_script.string:
        logger.warning("No __NEXT_DATA__ script found in the page")
        return None, None, {}
    
    try:
        data = json.loads(next_data_script.string)
        page_props = data.get("props", {}).get("pageProps", {})
        sale_id = page_props.get("saleId")
        
        if not sale_id:
            logger.warning("No sale ID found in the page data")
            return None, None, {}
        
        apollo_state = page_props.get("__APOLLO_STATE__", {})
        listing_key = f"SoldPropertyListing:{sale_id}"
        
        if listing_key not in apollo_state:
            logger.warning(f"Listing key {listing_key} not found in Apollo state")
            return None, None, {}
            
        listing_data = apollo_state[listing_key]
        original_listing_id = listing_data.get("listingId")
        sale_date_str = listing_data.get("formattedSoldAt", "")
        sale_date_datetime = parse_swedish_date(sale_date_str)
        
        # Extract only needed data
        extracted_data = {
            "title": f"{listing_data.get('housingForm', {}).get('name', '')} {listing_data.get('formattedLivingArea', '')} - {listing_data.get('locationName', '')}",
            "final_price": listing_data.get("sellingPrice", {}).get("amount") if listing_data.get("sellingPrice") else None,
            "sale_date_str": sale_date_str,
            "sale_date": parse_swedish_date(listing_data.get("formattedSoldAt")),
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
            "broker_agency": apollo_state.get(listing_data.get("brokerAgency", {}).get("__ref", ""), {}).get("name", "") if listing_data.get("brokerAgency") else ""            # ...other needed fields...
        }
        
        # Clean up large objects
        del data
        del page_props
        del apollo_state
        
        return sale_id, listing_data.get("listingId"), extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting data from JSON: {e}")
        return None, None, {}

def get_sold_listing_data(url, browser):
    logger.info(f"Fetching data for sold listing: {url}")
    
    with page_context(browser) as page:
        try:
            page.goto(url, wait_until="domcontentloaded")            
            html_content = page.content()
            sale_id, original_listing_id, json_data = extract_listing_data_from_json(html_content)
            
            if json_data:
                json_data["sale_hemnet_id"] = sale_id
                json_data["original_hemnet_id"] = original_listing_id
                json_data["url"] = url
                return json_data
            return {}
            
        except Exception as e:
            logger.error(f"Error processing sold listing {url}: {e}")
            return {}

def main():
    with browser_context() as (playwright, browser):
        try:
            consecutive_existing_count = 0
            
            for page in range(1, 51):                
                for url in get_sold_listing_urls(page, browser):
                    try:
                        data = get_sold_listing_data("https://www.hemnet.se" + url, browser)
                        if data:
                            success, already_exists = store_sold_listing(data)
                            
                            if already_exists:
                                consecutive_existing_count += 1
                                if consecutive_existing_count >= 50:
                                    logger.info("Found 50 consecutive existing sales, stopping execution")
                                    return
                            else:
                                consecutive_existing_count = 0
                            
                            # Clean up data after processing
                            del data
                            
                    except Exception as e:
                        logger.error(f"Error processing individual sold listing {url}: {e}")
                        consecutive_existing_count = 0
                        continue
                
                # Force garbage collection after each page
                gc.collect()
                
        except Exception as e:
            logger.error(f"Error in main page processing loop: {e}")

if __name__ == "__main__":
    main()