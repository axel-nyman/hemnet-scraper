from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, timedelta
from logging_setup import setup_logging
from playwright_utils import start_browser, close_browser

logger = setup_logging()

# Track exceptions and null fields
exceptions = list()
nulls = set()

def extract_data(listingData, locations, brokerAgencies, broker):
    try:
        data = dict()
        data["hemnet_id"] = int(listingData["id"])
        data["street_address"] = listingData["streetAddress"]
        data["post_code"] = listingData["postCode"]
        data["tenure"] = listingData["tenure"]["name"]
        data["number_of_rooms"] = int(listingData["numberOfRooms"]) if listingData["numberOfRooms"] else None
        if not listingData["askingPrice"]:
            return False
        data["asking_price"] = int(listingData["askingPrice"]["amount"])
        if listingData["squareMeterPrice"]:
            data["square_meter_price"] = int(listingData["squareMeterPrice"]["amount"])
        elif listingData["livingArea"]:
            data["square_meter_price"] = data["asking_price"] / int(listingData["livingArea"])
        else:
            data["square_meter_price"] = None
        data["fee"] = int(listingData["fee"]["amount"]) if listingData["fee"] else None
        data["yearly_arrende_fee"] = int("".join(listingData["yearlyArrendeFee"]["formatted"].strip("kr").split())) if listingData["yearlyArrendeFee"] else None
        data["yearly_leasehold_fee"] = int("".join(listingData["yearlyLeaseholdFee"]["formatted"].strip("kr").split())) if listingData["yearlyLeaseholdFee"] else None
        data["running_costs"] = int(listingData["runningCosts"]["amount"]) if listingData["runningCosts"] else None
        data["construction_year"] = int(listingData["legacyConstructionYear"]) if listingData["legacyConstructionYear"] else None
        data["living_area"] = int(listingData["livingArea"]) if listingData["livingArea"] else None
        data["is_foreclosure"] = listingData["isForeclosure"]
        data["is_new_construction"] = listingData["isNewConstruction"]
        data["is_project"] = listingData["isProject"]
        data["is_upcoming"] = listingData["isUpcoming"]
        data["supplemental_area"] = int(listingData["supplementalArea"]) if listingData["supplementalArea"] else None
        data["land_area"] = int(listingData["landArea"]) if listingData["landArea"] else None
        data["housing_form"] = listingData["housingForm"]["name"]
        data["relevant_amenities"] = dict()
        data["energy_classification"] = listingData["energyClassification"]["classification"] if listingData["energyClassification"] else None
        data["floor"] = int(listingData["formattedFloor"][:2].strip().strip(",")) if listingData["formattedFloor"] else None
        data["published_date"] = (datetime.now() - timedelta(days=int(listingData["daysOnHemnet"]))).strftime('%Y-%m-%d')
        data["locations"] = locations
        data["broker_agencies"] = brokerAgencies
        data["broker"] = broker
        data["description"] = listingData["description"]
        data["closest_water_distance_meters"] = int(listingData["closestWaterDistanceMeters"]) if listingData["closestWaterDistanceMeters"] else None
        data["coastline_distance_meters"] = int(listingData["coastlineDistanceMeters"]) if listingData["coastlineDistanceMeters"] else None

        for amenity in listingData["relevantAmenities"]:
            data["relevant_amenities"][amenity["title"]] = amenity["isAvailable"]

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

def get_listing_urls(page_number, browser, base_url):
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

def get_listing_data(url, browser):
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
            logger.debug(f"Successfully extracted data for listing {dataToStore.get('hemnet_id', 'unknown')}")
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

def save_to_database(data):
    #TODO: Implement your database saving logic here
    pass

def listing_exists_in_database(hemnet_id):
    #TODO: Implement your logic to check if the listing already exists in the database
    return False

def main():
    playwright, browser = start_browser()
    base_url = "https://www.hemnet.se"
    
    try:
        for x in range(1, 51):
            hrefs = get_listing_urls(x, browser, base_url)
            logger.info(f"Processing {len(hrefs)} listings from page {x}")
            
            for href in hrefs:
                try:
                    listingData = get_listing_data(base_url + href, browser)
                    if listingData:
                        if not listing_exists_in_database(listingData["hemnet_id"]):
                            save_to_database(listingData)
                        else:
                            logger.info(f"Listing {listingData['hemnet_id']} already exists in the database")
                except Exception as e:
                    logger.error(f"Error processing individual listing {href}: {e}")
                    exceptions.append(e)
                    continue
    except Exception as e:
        logger.error(f"Error in main page processing loop: {e}")
        exceptions.append(e)
    finally:
        close_browser(playwright, browser)
        logger.info(f"Script completed. Encountered {len(exceptions)} exceptions")
        logger.info(f"Fields with null values: {nulls}")

if __name__ == "__main__":
    main()