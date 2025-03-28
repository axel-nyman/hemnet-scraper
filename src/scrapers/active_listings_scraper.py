import gc
from bs4 import BeautifulSoup, SoupStrainer
import json
from datetime import datetime, timedelta
from utils.logging_setup import setup_logging
from utils.playwright_utils import browser_context, page_context
from utils.database_utils import listing_exists_in_database, save_to_database

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
        data["housing_cooperative"] = listingData["housingCooperative"] if listingData["housingCooperative"] else None
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
    webpage = f"/bostader{'?page=' + str(page_number) if page_number > 1 else ''}"
    logger.info(f"Fetching listings from page {page_number}: {webpage}")        
    
    with page_context(browser) as page:
        page.goto(base_url + webpage, wait_until="domcontentloaded")
        content = page.content()
        # Parse only the needed elements instead of the entire page
        soup = BeautifulSoup(content, 'html.parser', parse_only=SoupStrainer('div', attrs={'data-testid': 'result-list'}))
        
        if not soup:
            logger.warning(f"Result list not found on page {page_number}")
            return

        for link in soup.find_all('a', href=True):
            if link['href'].startswith('/bostad'):
                yield link['href']

def get_listing_data(url, browser):
    with page_context(browser) as page:
        try:
            page.goto(url, wait_until="domcontentloaded")
            # Parse only the needed element
            soup = BeautifulSoup(page.content(), 'html.parser', 
                               parse_only=SoupStrainer('script', id='__NEXT_DATA__'))
            
            next_data = soup.find()
            if not next_data:
                logger.warning(f"__NEXT_DATA__ not found for listing: {url}")
                return False

            data = json.loads(next_data.string)
            apollo_state = data["props"]["pageProps"]["__APOLLO_STATE__"]
            
            # Process data in smaller chunks
            locations = [
                {"hemnetId": int(v["id"]), "name": v["fullName"]}
                for k, v in apollo_state.items()
                if k.startswith("Location:")
            ]
            
            brokerAgencies = [
                {"hemnetId": int(v["id"]), "name": v["name"]}
                for k, v in apollo_state.items()
                if k.startswith("BrokerAgency:")
            ]
            
            broker = next(
                ({"hemnetId": int(v["id"]), "name": v["name"]}
                for k, v in apollo_state.items()
                if k.startswith("Broker:")),
                {}
            )
            
            listingData = next(
                (v for k, v in apollo_state.items()
                if k.startswith(("ActivePropertyListing:", "ProjectUnit:", "DeactivatedBeforeOpenHousePropertyListing:"))),
                None
            )

            if not listingData:
                logger.warning(f"No listing data found for {url}")
                return False

            # Clear variables explicitly
            del data
            del apollo_state
            del soup
            
            return extract_data(listingData, locations, brokerAgencies, broker)
            
        except Exception as e:
            logger.error(f"Error processing listing {url}: {e}")
            exceptions.append(e)
            return False

def main():
    with browser_context() as (playwright, browser):
        base_url = "https://www.hemnet.se"
        consecutive_existing_count = 0
        
        try:
            for x in range(1, 51):
                for href in get_listing_urls(x, browser, base_url):
                    try:
                        listingData = get_listing_data(base_url + href, browser)
                        if listingData:
                            hemnet_id = listingData["hemnet_id"]
                            if not listing_exists_in_database(hemnet_id):
                                if save_to_database(listingData):
                                    logger.info(f"Successfully saved listing {hemnet_id}")
                                    consecutive_existing_count = 0
                                else:
                                    logger.warning(f"Failed to save listing {hemnet_id}")
                            else:
                                consecutive_existing_count += 1
                                if consecutive_existing_count >= 50:
                                    return
                        del listingData
                    except Exception as e:
                        logger.error(f"Error processing listing {href}: {e}")
                        consecutive_existing_count = 0
                        continue
                
                # Force garbage collection after each page
                gc.collect()
                
        except Exception as e:
            logger.error(f"Fatal error in main: {e}")
            raise
        finally:
            logger.info(f"Script completed. Encountered {len(exceptions)} exceptions")
            logger.info(f"Fields with null values: {nulls}")
        
if __name__ == "__main__":
    main()