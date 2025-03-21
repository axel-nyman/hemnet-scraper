from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import logging
import os
from datetime import datetime

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

# Track exceptions and null fields
exceptions = list()
nulls = set()

def extract_data(listingData, locations, brokerAgencies, broker):
    try:
        data = dict()
        data["hemnetId"] = int(listingData["id"])
        data["streetAddress"] = listingData["streetAddress"]
        data["postCode"] = listingData["postCode"]
        data["tenure"] = listingData["tenure"]["name"]
        data["numberOfRooms"] = int(listingData["numberOfRooms"]) if listingData["numberOfRooms"] else None
        data["askingPrice"] = int(listingData["askingPrice"]["amount"]) if listingData["askingPrice"] else None
        data["squareMeterPrice"] = int(listingData["squareMeterPrice"]["amount"]) if listingData["squareMeterPrice"] else None
        data["fee"] = int(listingData["fee"]["amount"]) if listingData["fee"] else None
        data["yearlyArrendeFee"] = int("".join(listingData["yearlyArrendeFee"]["formatted"].strip("kr").split())) if listingData["yearlyArrendeFee"] else None
        data["yearlyLeaseholdFee"] = int("".join(listingData["yearlyLeaseholdFee"]["formatted"].strip("kr").split())) if listingData["yearlyLeaseholdFee"] else None
        data["runningCosts"] = int(listingData["runningCosts"]["amount"]) if listingData["runningCosts"] else None
        data["legacyConstructionYear"] = int(listingData["legacyConstructionYear"]) if listingData["legacyConstructionYear"] else None
        data["area"] = listingData["area"]
        data["livingArea"] = int(listingData["livingArea"]) if listingData["livingArea"] else None
        data["isForeclosure"] = listingData["isForeclosure"]
        data["isNewConstruction"] = listingData["isNewConstruction"]
        data["isProject"] = listingData["isProject"]
        data["isUpcoming"] = listingData["isUpcoming"]
        data["supplementalArea"] = int(listingData["supplementalArea"]) if listingData["supplementalArea"] else None
        data["landArea"] = int(listingData["landArea"]) if listingData["landArea"] else None
        data["housingForm"] = listingData["housingForm"]["name"]
        data["relevantAmenities"] = dict()
        data["energyClassification"] = listingData["energyClassification"]["classification"] if listingData["energyClassification"] else None
        data["floor"] = int(listingData["formattedFloor"][:2].strip().strip(",")) if listingData["formattedFloor"] else None
        data["daysSincePublished"] = int(listingData["daysOnHemnet"])
        data["locations"] = locations
        data["brokerAgencies"] = brokerAgencies
        data["broker"] = broker
        data["description"] = listingData["description"]
        data["closestWaterDistanceMeters"] = int(listingData["closestWaterDistanceMeters"]) if listingData["closestWaterDistanceMeters"] else None
        data["coastlineDistanceMeters"] = int(listingData["coastlineDistanceMeters"]) if listingData["coastlineDistanceMeters"] else None

        for amenity in listingData["relevantAmenities"]:
            data["relevantAmenities"][amenity["title"]] = amenity["isAvailable"]

        for breadcrumb in listingData["breadcrumbs"]:
            id = int(breadcrumb["path"].split("=")[-1])
            for location in locations:
                if id == location["hemnetId"]:
                    location["type"] = breadcrumb["trackingValue"]
        return data
    except KeyError as e:
        logger.error(f"KeyError in extract_data: {e}")
        logger.debug(f"Local variables: {e.__traceback__.tb_frame.f_locals}")
        exceptions.append(e)
        return False
    except Exception as e:
        logger.error(f"Exception in extract_data: {e}")
        logger.debug(f"Local variables: {e.__traceback__.tb_frame.f_locals}")
        exceptions.append(e)
        return False

with sync_playwright() as playwright:
    base_url = "https://www.hemnet.se"
    
    try:
        logger.info("Starting browser session")
        browser = playwright.webkit.launch()
        
        def get_listing_urls(page_number):
            listings = list()
            webpage = "/bostader"
            webpage = "/bostader?page=" + str(page_number) if page_number > 1 else webpage
            logger.info(f"Fetching listings from page {page_number}: {webpage}")        
            
            try:
                page = browser.new_page()
                page.goto(base_url + webpage)
                soup = BeautifulSoup(page.content(), 'html.parser')
                result_list = soup.find('div', attrs={'data-testid': 'result-list'})
                
                if not result_list:
                    logger.warning(f"Result list not found on page {page_number}")
                    page.close()
                    return listings
                
                for link in result_list.find_all('a'):
                    href = link.get('href')
                    if href and href.startswith('/bostad'):
                        listings.append(href)
                
                logger.info(f"Found {len(listings)} listings on page {page_number}")
                page.close()
                return listings
            except Exception as e:
                logger.error(f"Error fetching listing URLs from page {page_number}: {e}")
                exceptions.append(e)
                if 'page' in locals() and page:
                    page.close()
                return []

        def get_listing_data(url):
            logger.info(f"Fetching data for listing: {url}")
            try:
                page = browser.new_page()
                page.goto(url)
                soup = BeautifulSoup(page.content(), 'html.parser')
                next_data = soup.find(id='__NEXT_DATA__')
                
                if not next_data:
                    logger.warning(f"__NEXT_DATA__ not found for listing: {url}")
                    page.close()
                    return False
                
                temp = json.loads(next_data.text)
                
                try:
                    allData = temp["props"]["pageProps"]["__APOLLO_STATE__"]
                except KeyError as e:
                    logger.error(f"KeyError accessing APOLLO_STATE: {e}")
                    exceptions.append(e)
                    page.close()
                    return False
                
                locations = list()
                brokerAgencies = list()
                broker = dict()
                listingData = dict()
                
                for key in allData.keys():
                    if key.startswith("Location:"):
                        locations.append({"hemnetId": int(allData[key]["id"]), "name": allData[key]["fullName"]})
                    elif key.startswith("BrokerAgency:"):
                        brokerAgencies.append({"hemnetId": int(allData[key]["id"]), "name": allData[key]["name"]})
                    elif key.startswith("Broker:"):
                        broker["hemnetId"] = int(allData[key]["id"])
                        broker["name"] = allData[key]["name"]
                    elif key.startswith("ActivePropertyListing:") or key.startswith("ProjectUnit:") or key.startswith("DeactivatedBeforeOpenHousePropertyListing:"):
                        listingData = allData[key]
                
                if not listingData:
                    logger.warning(f"No listing data found for {url}")
                    page.close()
                    return False
                
                dataToStore = extract_data(listingData, locations, brokerAgencies, broker)
                if dataToStore:
                    logger.debug(f"Successfully extracted data for listing {dataToStore.get('hemnetId', 'unknown')}")
                    for key, value in dataToStore.items():
                        if value is None:
                            nulls.add(key)
                else:
                    logger.warning(f"Failed to extract data for listing: {url}")
                
                page.close()
                return dataToStore
            except Exception as e:
                logger.error(f"Error processing listing {url}: {e}")
                exceptions.append(e)
                if 'page' in locals() and page:
                    page.close()
                return False
        
        try:
            for x in range(1, 51):
                hrefs = get_listing_urls(x)
                logger.info(f"Processing {len(hrefs)} listings from page {x}")
                
                for href in hrefs:
                    try:
                        listingData = get_listing_data(base_url + href)
                        # if listingData:
                        #     logger.debug(f"Listing data: {json.dumps(listingData, indent=4, ensure_ascii=False)}")
                        #TODO: Check if listing already exists in database
                        #TODO: Save allData to database
                    except Exception as e:
                        logger.error(f"Error processing individual listing {href}: {e}")
                        exceptions.append(e)
                        continue
        except Exception as e:
            logger.error(f"Error in main page processing loop: {e}")
            exceptions.append(e)
        
        # listingData = get_listing_data(base_url + "/bostad/villa-4rum-kolboda-kalmar-kommun-skarvvagen-54-21364403")
        # logger.debug(json.dumps(listingData, indent=4, ensure_ascii=False))
    
    except Exception as e:
        logger.critical(f"Critical error in main script execution: {e}")
        exceptions.append(e)
    finally:
        if 'browser' in locals() and browser:
            logger.info("Closing browser session")
            browser.close()
        
        logger.info(f"Script completed. Encountered {len(exceptions)} exceptions")
        logger.info(f"Fields with null values: {nulls}")

        # Listing examples with special cases
        logger.debug("Special case examples:")
        logger.debug("Listing with only two breadcrumbs: /bostad/villa-5rum-nykvarns-kommun-kopparhaga-1-21489899")
        logger.debug("Listing with yearly arrendee fee: /bostad/fritidsboende-3rum-larje-hed-goteborgs-kommun-larjeheds-fritidsomrade-stuga-nr-49-21490507")
        logger.debug("Listing without asking price: /bostad/villa-6rum-replosa-ljungby-kommun-satervagen-13-21411964")
        logger.debug("Listing without key \"activePropertyListing\": /bostad/lagenhet-3rum-sanden-vanersborgs-kommun-brogatan-3a-18747455")
        logger.debug("Listing on floor \"-2\": /bostad/lagenhet-1rum-nedre-haga-sundsvalls-kommun-skonsbergsvagen-31a-21490553")
        logger.debug("Listing with yearly lease hold fee: /bostad/villa-4rum-soderhamn-centrum-soderhamns-kommun-tegvagen-6-21490423")
        logger.debug("Listing of type deactivated before open house: /bostad/villa-4rum-kolboda-kalmar-kommun-skarvvagen-54-21364403")