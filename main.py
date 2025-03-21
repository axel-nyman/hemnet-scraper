from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json

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
        print(f"KeyError: {e}")
        print(e.__traceback__.tb_frame.f_locals)
        exceptions.append(e)
        return False
    except Exception as e:
        print(f"Exception: {e}")
        print(e.__traceback__.tb_frame.f_locals)
        exceptions.append(e)
        return False

with sync_playwright() as playwright:
    base_url = "https://www.hemnet.se"
    browser = playwright.webkit.launch()
    
    def get_listing_urls(page_number):
        listings = list()
        webpage = "/bostader"
        webpage = "/bostader?page=" + str(page_number) if page_number > 1 else webpage
        print(webpage)        
        page = browser.new_page()
        page.goto(base_url + webpage)
        soup = BeautifulSoup(page.content(), 'html.parser')
        for link in soup.find('div', attrs={'data-testid': 'result-list'}).find_all('a'):
            href = link.get('href')
            if href.startswith('/bostad'):
                listings.append(href)
        page.close()
        return listings

    def get_listing_data(url):
        page = browser.new_page()
        page.goto(url)
        soup = BeautifulSoup(page.content(), 'html.parser')
        temp = json.loads(soup.find(id='__NEXT_DATA__').text)
        
        try:
            allData = temp["props"]["pageProps"]["__APOLLO_STATE__"]
        except KeyError as e:
            print(f"KeyError: {e}")
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
        dataToStore = extract_data(listingData, locations, brokerAgencies, broker)
        if dataToStore:
            for key, value in dataToStore.items():
                if value is None:
                    nulls.add(key)
        page.close()
        return dataToStore
    
    for x in range(1, 51):
        hrefs = get_listing_urls(x)
        for href in hrefs:
            print(href)
            listingData = get_listing_data(base_url + href)
            # if listingData:
            #     print(json.dumps(listingData, indent=4, ensure_ascii=False))
            #TODO: Check if listing already exists in database
            #TODO: Save allData to database
    
    # listingData = get_listing_data(base_url + "/bostad/villa-4rum-kolboda-kalmar-kommun-skarvvagen-54-21364403")
    # print(json.dumps(listingData, indent=4, ensure_ascii=False))
    
    browser.close()
    print(exceptions)
    print(nulls)

    # Listing with only two breadcrumbs: /bostad/villa-5rum-nykvarns-kommun-kopparhaga-1-21489899
    # Listing with yearly arrendee fee: /bostad/fritidsboende-3rum-larje-hed-goteborgs-kommun-larjeheds-fritidsomrade-stuga-nr-49-21490507
    # Listing without asking price: /bostad/villa-6rum-replosa-ljungby-kommun-satervagen-13-21411964
    # Listing without key "activePropertyListing": /bostad/lagenhet-3rum-sanden-vanersborgs-kommun-brogatan-3a-18747455
    # Listing on floor "-2": /bostad/lagenhet-1rum-nedre-haga-sundsvalls-kommun-skonsbergsvagen-31a-21490553
    # Listing with yearly lease hold fee: /bostad/villa-4rum-soderhamn-centrum-soderhamns-kommun-tegvagen-6-21490423
    # Listing of type deactivated before open house: /bostad/villa-4rum-kolboda-kalmar-kommun-skarvvagen-54-21364403