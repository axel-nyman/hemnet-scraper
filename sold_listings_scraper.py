from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime
import locale
from logging_setup import setup_logging
from playwright_utils import start_browser, close_browser

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

def extract_listing_data_from_json(html_content):
    """Extract all listing data from the embedded JSON in the page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the Next.js data script
    next_data_script = soup.find("script", id="__NEXT_DATA__")
    
    if not next_data_script or not next_data_script.string:
        logger.warning("No __NEXT_DATA__ script found in the page")
        return None, None, {}
    
    try:
        # Parse the JSON data
        data = json.loads(next_data_script.string)
        
        # Navigate to the relevant sections
        page_props = data.get("props", {}).get("pageProps", {})
        sale_id = page_props.get("saleId")
        
        if not sale_id:
            logger.warning("No sale ID found in the page data")
            return None, None, {}
        
        # Get Apollo state which contains the listing data
        apollo_state = page_props.get("__APOLLO_STATE__", {})
        
        # Find the listing data using the sale ID
        listing_key = f"SoldPropertyListing:{sale_id}"
        
        if listing_key not in apollo_state:
            logger.warning(f"Listing key {listing_key} not found in Apollo state")
            return None, None, {}
            
        listing_data = apollo_state[listing_key]
        original_listing_id = listing_data.get("listingId")
        sale_date_str = listing_data.get("formattedSoldAt", "")
        sale_date_datetime = parse_swedish_date(sale_date_str)
        
        # Extract using amount values instead of formatted values
        extracted_data = {
            "title": f"{listing_data.get('housingForm', {}).get('name', '')} {listing_data.get('formattedLivingArea', '')} - {listing_data.get('locationName', '')}",
            "final_price": listing_data.get("sellingPrice", {}).get("amount") if listing_data.get("sellingPrice") else None,
            "sale_date_str": sale_date_str,
            "sale_date": sale_date_datetime.strftime('%Y-%m-%d') if sale_date_datetime else None,
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
        
        logger.info(f"Successfully extracted JSON data for sold listing {sale_id}")
        return sale_id, original_listing_id, extracted_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON data: {e}")
    except Exception as e:
        logger.error(f"Error extracting data from JSON: {e}")
    
    return None, None, {}

def get_sold_listing_data(url, browser):
    logger.info(f"Fetching data for sold listing: {url}")
    try:
        page = browser.new_page()
        page.goto(url)
        html_content = page.content()
        
        # Extract data from JSON
        sale_id, original_listing_id, json_data = extract_listing_data_from_json(html_content)
        
        if json_data:
            json_data["sale_hemnet_id"] = sale_id
            json_data["original_hemnet_id"] = original_listing_id
            json_data["url"] = url
            
            logger.info(f"Successfully processed data for sold listing {sale_id}")
            page.close()
            return json_data
        else:
            logger.warning(f"No data extracted for {url}")
            page.close()
            return {}
    except Exception as e:
        logger.error(f"Error processing sold listing {url}: {e}")
        if 'page' in locals() and page:
            page.close()
        return {}

def store_sold_listing(data):
    # Placeholder function for future database implementation
    pass

def scrape_sold_listings():
    playwright, browser = start_browser()
    
    try:
        for page in range(1, 51):
            urls = get_sold_listing_urls(page, browser)
            logger.info(f"Processing {len(urls)} sold listings from page {page}")
            
            for url in urls:
                try:
                    data = get_sold_listing_data("https://www.hemnet.se" + url, browser)
                    if data:
                        store_sold_listing(data)
                    else:
                        logger.warning(f"No data returned for {url}")
                except Exception as e:
                    logger.error(f"Error processing individual sold listing {url}: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error in main page processing loop: {e}")
    finally:
        close_browser(playwright, browser)
        logger.info("Scraping complete.")

if __name__ == "__main__":
    scrape_sold_listings()