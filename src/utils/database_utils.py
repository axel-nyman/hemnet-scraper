import psycopg2
import logging
import os
import time

logger = logging.getLogger(__name__)


def get_db_connection():
    """
    Create and return a connection to the PostgreSQL database with retry logic for containers.
    """
    max_retries = 5
    retry_delay = 2  # seconds
    
    # Get connection parameters from environment variables with fallbacks
    db_host = os.environ.get("DB_HOST", "db")  # Use 'db' as default (common service name)
    db_name = os.environ.get("DB_NAME", "real_estate")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "")
    db_port = os.environ.get("DB_PORT", "5432")
    
    # Retry logic for container startup order
    retry_count = 0
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            return conn
        except psycopg2.OperationalError as e:
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Database connection attempt {retry_count} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise

def check_or_create_lookup_value(conn, table, id_column, name_column, value):
    """
    Check if a lookup value exists in the specified table. If not, create it.
    Returns the ID of the existing or newly created record.
    
    Args:
        conn: Database connection
        table: Table name (e.g., 'housing_form_types')
        id_column: ID column name (e.g., 'housing_form_id')
        name_column: Name column name (e.g., 'name')
        value: The value to look up or create
        
    Returns:
        The ID of the existing or newly created record
    """
    cursor = conn.cursor()
    try:
        # Check if the value already exists
        cursor.execute(f"SELECT {id_column} FROM {table} WHERE {name_column} = %s", (value,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # If not, create it
        cursor.execute(
            f"INSERT INTO {table} ({name_column}) VALUES (%s) RETURNING {id_column}", 
            (value,)
        )
        new_id = cursor.fetchone()[0]
        conn.commit()
        return new_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in check_or_create_lookup_value for {table}: {e}")
        raise
    finally:
        cursor.close()

def get_or_create_broker(conn, broker_data):
    """
    Get or create a broker record in the database.
    Returns the broker_id.
    """
    cursor = conn.cursor()
    try:
        hemnet_id = broker_data.get("hemnetId")
        name = broker_data.get("name")
        
        if not hemnet_id or not name:
            logger.error("Missing required broker data")
            return None
        
        # Check if broker exists
        cursor.execute("SELECT broker_id FROM brokers WHERE broker_hemnet_id = %s", (hemnet_id,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new broker
        cursor.execute(
            "INSERT INTO brokers (broker_hemnet_id, name) VALUES (%s, %s) RETURNING broker_id",
            (hemnet_id, name)
        )
        broker_id = cursor.fetchone()[0]
        conn.commit()
        return broker_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_broker: {e}")
        raise
    finally:
        cursor.close()

def get_or_create_agency(conn, agency_data):
    """
    Get or create a broker agency record in the database.
    Returns the agency_id.
    """
    cursor = conn.cursor()
    try:
        hemnet_id = agency_data.get("hemnetId")
        name = agency_data.get("name")
        
        if not hemnet_id or not name:
            logger.error("Missing required agency data")
            return None
        
        # Check if agency exists
        cursor.execute("SELECT agency_id FROM broker_agencies WHERE agency_hemnet_id = %s", (hemnet_id,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new agency
        cursor.execute(
            "INSERT INTO broker_agencies (agency_hemnet_id, name) VALUES (%s, %s) RETURNING agency_id",
            (hemnet_id, name)
        )
        agency_id = cursor.fetchone()[0]
        conn.commit()
        return agency_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_agency: {e}")
        raise
    finally:
        cursor.close()

def get_or_create_housing_cooperative(conn, housing_cooperative_data):
    """
    Get or create a housing cooperative record in the database.
    Returns the housing_cooperative_id.
    
    Args:
        conn: Database connection
        housing_cooperative_data: Dictionary containing housing cooperative data
        
    Returns:
        The housing_cooperative_id if successful, None otherwise
    """
    cursor = conn.cursor()
    try:
        # Extract data
        name = housing_cooperative_data.get("name")
        
        if not name:
            logger.error("Missing required housing cooperative data: name")
            return None
        
        # Check if the housing cooperative exists
        cursor.execute("SELECT housing_cooperative_id FROM housing_cooperatives WHERE name = %s", (name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new housing cooperative
        cursor.execute(
            "INSERT INTO housing_cooperatives (name) VALUES (%s) RETURNING housing_cooperative_id",
            (name,)
        )
        housing_cooperative_id = cursor.fetchone()[0]
        conn.commit()
        return housing_cooperative_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_housing_cooperative: {e}")
        raise
    finally:
        cursor.close()

def create_broker_agency_relationship(conn, broker_id, agency_id):
    """
    Create a relationship between broker and agency if it doesn't exist.
    """
    if not broker_id or not agency_id:
        return
    
    cursor = conn.cursor()
    try:
        # Check if relationship exists
        cursor.execute(
            "SELECT 1 FROM broker_agency_relationships WHERE broker_id = %s AND agency_id = %s AND end_date IS NULL",
            (broker_id, agency_id)
        )
        if cursor.fetchone():
            return  # Relationship already exists
        
        # Check if there was a previous relationship that ended
        cursor.execute(
            "SELECT 1 FROM broker_agency_relationships WHERE broker_id = %s AND agency_id = %s",
            (broker_id, agency_id)
        )
        if cursor.fetchone():
            # Update the end_date of previous relationship to ensure we don't create duplicates
            cursor.execute(
                "UPDATE broker_agency_relationships SET is_active = FALSE, end_date = CURRENT_DATE "
                "WHERE broker_id = %s AND agency_id = %s AND end_date IS NULL",
                (broker_id, agency_id)
            )
        
        # Create new relationship
        cursor.execute(
            "INSERT INTO broker_agency_relationships (broker_id, agency_id) VALUES (%s, %s)",
            (broker_id, agency_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in create_broker_agency_relationship: {e}")
    finally:
        cursor.close()

def get_or_create_location(conn, location_data):
    """
    Get or create a location record in the database.
    Returns the location_id.
    """
    cursor = conn.cursor()
    try:
        hemnet_id = location_data.get("hemnetId")
        name = location_data.get("name")
        location_type = location_data.get("type")
        
        if not hemnet_id or not name:
            logger.error("Missing required location data")
            return None
        
        # Check if location exists
        cursor.execute("SELECT location_id FROM locations WHERE location_hemnet_id = %s", (hemnet_id,))
        result = cursor.fetchone()
        
        if result:
            # Update type if needed
            if location_type and result[0]:
                cursor.execute(
                    "UPDATE locations SET type = %s WHERE location_id = %s",
                    (location_type, result[0])
                )
                conn.commit()
            return result[0]
        
        # Create new location
        cursor.execute(
            "INSERT INTO locations (location_hemnet_id, location_name, type) "
            "VALUES (%s, %s, %s) RETURNING location_id",
            (hemnet_id, name, location_type)
        )
        location_id = cursor.fetchone()[0]
        conn.commit()
        return location_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_location: {e}")
        raise
    finally:
        cursor.close()

def get_or_create_amenity(conn, amenity_name):
    """
    Get or create an amenity record in the database.
    Returns the amenity_id.
    """
    cursor = conn.cursor()
    try:
        # Check if amenity exists
        cursor.execute("SELECT amenity_id FROM amenities WHERE amenity_name = %s", (amenity_name,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Create new amenity
        cursor.execute(
            "INSERT INTO amenities (amenity_name) VALUES (%s) RETURNING amenity_id",
            (amenity_name,)
        )
        amenity_id = cursor.fetchone()[0]
        conn.commit()
        return amenity_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in get_or_create_amenity: {e}")
        raise
    finally:
        cursor.close()

def listing_exists_in_database(hemnet_id):
    """
    Check if a listing with the given Hemnet ID already exists in the database.
    
    Args:
        hemnet_id: The Hemnet ID to check
        
    Returns:
        Boolean indicating whether the listing exists
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM listings WHERE listing_hemnet_id = %s", (hemnet_id,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return exists
    except Exception as e:
        logger.error(f"Error checking if listing exists: {e}")
        return False

def save_to_database(data):
    """
    Save the scraped listing data to the database.
    
    Args:
        data: Dictionary containing the listing data
        
    Returns:
        Boolean indicating success or failure
    """
    if not data or not data.get("hemnet_id"):
        logger.error("Invalid listing data, missing hemnet_id")
        return False
    
    try:
        conn = get_db_connection()
        
        # 1. Process lookup values
        housing_form_id = check_or_create_lookup_value(
            conn, "housing_form_types", "housing_form_id", "name", data["housing_form"]
        )
        
        tenure_id = check_or_create_lookup_value(
            conn, "tenure_types", "tenure_id", "name", data["tenure"]
        )
        
        energy_classification_id = None
        if data["energy_classification"]:
            energy_classification_id = check_or_create_lookup_value(
                conn, "energy_classifications", "energy_classification_id", "classification", 
                data["energy_classification"]
            )
        
        # Process housing cooperative if it exists
        housing_cooperative_id = None
        if data.get("housing_cooperative") and data["housing_cooperative"].get("name"):
            housing_cooperative_id = get_or_create_housing_cooperative(conn, data["housing_cooperative"])
        
        # 2. Get or create broker
        broker_id = get_or_create_broker(conn, data["broker"])
        
        # 3. Insert the listing
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO listings (
                    listing_hemnet_id, url, street_address, postcode, tenure_id, number_of_rooms,
                    asking_price, squaremeter_price, fee, yearly_arrendee_fee, yearly_leasehold_fee,
                    running_costs, construction_year, living_area, is_foreclosure, is_new_construction,
                    is_project, is_upcoming, supplemental_area, land_area, housing_form_id,
                    housing_cooperative_id, energy_classification_id, floor, published_date, broker_id,
                    closest_water_distance_meters, coastline_distance_meters, description,
                    latitude, longitude
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING listing_id
            """, (
                data["hemnet_id"],
                f"https://www.hemnet.se/bostad/{data['hemnet_id']}",
                data["street_address"],
                data.get("post_code"),
                tenure_id,
                data.get("number_of_rooms"),
                data["asking_price"],
                data.get("square_meter_price"),
                data.get("fee"),
                data.get("yearly_arrende_fee"),
                data.get("yearly_leasehold_fee"),
                data.get("running_costs"),
                data.get("construction_year"),
                data.get("living_area"),
                data["is_foreclosure"],
                data["is_new_construction"],
                data["is_project"],
                data["is_upcoming"],
                data.get("supplemental_area"),
                data.get("land_area"),
                housing_form_id,
                housing_cooperative_id,
                energy_classification_id,
                data.get("floor"),
                data["published_date"],
                broker_id,
                data.get("closest_water_distance_meters"),
                data.get("coastline_distance_meters"),
                data.get("description"),
                None,  # latitude - not provided in your extraction method, add if needed
                None   # longitude - not provided in your extraction method, add if needed
            ))
            
            listing_id = cursor.fetchone()[0]
            
            # 4. Process agency relationships
            for agency_data in data["broker_agencies"]:
                agency_id = get_or_create_agency(conn, agency_data)
                if agency_id:
                    create_broker_agency_relationship(conn, broker_id, agency_id)
                    
                    # Create listing-agency relationship
                    cursor.execute(
                        "INSERT INTO listing_agencies (listing_id, agency_id) VALUES (%s, %s)",
                        (listing_id, agency_id)
                    )
            
            # 5. Process locations
            for location_data in data["locations"]:
                location_id = get_or_create_location(conn, location_data)
                if location_id:
                    cursor.execute(
                        "INSERT INTO listing_locations (listing_id, location_id) VALUES (%s, %s)",
                        (listing_id, location_id)
                    )
            
            # 6. Process amenities
            for amenity_name, is_available in data["relevant_amenities"].items():
                if is_available:
                    amenity_id = get_or_create_amenity(conn, amenity_name)
                    if amenity_id:
                        cursor.execute(
                            "INSERT INTO listing_amenities (listing_id, amenity_id) VALUES (%s, %s)",
                            (listing_id, amenity_id)
                        )
            
            conn.commit()
            logger.info(f"Successfully saved listing {data['hemnet_id']} to database")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error inserting listing {data['hemnet_id']}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Database error while saving listing {data.get('hemnet_id')}: {e}")
        return False
    
def sale_exists_in_database(sale_hemnet_id):
    """
    Check if a sale with the given Hemnet ID already exists in the database.
    
    Args:
        sale_hemnet_id: The Hemnet sale ID to check
        
    Returns:
        Boolean indicating whether the sale exists
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM property_sales WHERE sale_hemnet_id = %s", (sale_hemnet_id,))
        exists = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return exists
    except Exception as e:
        logger.error(f"Error checking if sale exists: {e}")
        return False

def find_matching_listing_id(original_hemnet_id):
    """
    Find the internal listing_id for a given Hemnet listing ID
    
    Args:
        original_hemnet_id: The original Hemnet listing ID
        
    Returns:
        The internal listing_id if found, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT listing_id FROM listings WHERE listing_hemnet_id = %s", (original_hemnet_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error finding matching listing ID: {e}")
        return None

def store_sold_listing(data):
    """
    Store the sold listing data in the database.
    
    Args:
        data: Dictionary containing the sold listing data
        
    Returns:
        tuple: (success: bool, already_exists: bool)
    """
    if not data or not data.get("sale_hemnet_id"):
        logger.error("Invalid sold listing data, missing sale_hemnet_id")
        return False, False
    
    sale_hemnet_id = data.get("sale_hemnet_id")
    
    # Check if this sale already exists in our database
    if sale_exists_in_database(sale_hemnet_id):
        logger.info(f"Sale {sale_hemnet_id} already exists in database, skipping")
        return False, True  # Not stored, already exists
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find matching listing_id if we have the original listing
        original_hemnet_id = data.get("original_hemnet_id")
        listing_id = None
        if original_hemnet_id:
            listing_id = find_matching_listing_id(original_hemnet_id)
        
        # Insert the property sale data
        cursor.execute("""
            INSERT INTO property_sales (
                sale_hemnet_id, listing_id, listing_hemnet_id, final_price, asking_price,
                price_change, price_change_percentage, sale_date, sale_date_str,
                broker_agency, living_area, land_area, number_of_rooms, construction_year,
                street_address, area, municipality, running_costs, url
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            sale_hemnet_id,
            listing_id,
            data.get("original_hemnet_id"),
            data.get("final_price"),
            data.get("asking_price"),
            data.get("price_change"),
            data.get("price_change_percentage"),
            data.get("sale_date"),
            data.get("sale_date_str"),
            data.get("broker_agency"),
            data.get("living_area"),
            data.get("land_area"),
            data.get("rooms"),
            data.get("construction_year"),
            data.get("street_address"),
            data.get("area"),
            data.get("municipality"),
            data.get("running_costs"),
            data.get("url")
        ))
        
        # Update status of the original listing if we found a match
        if listing_id:
            cursor.execute("""
                UPDATE listings 
                SET status = 'sold' 
                WHERE listing_id = %s
            """, (listing_id,))
            logger.info(f"Updated status of listing {listing_id} to 'sold'")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully saved sold listing {sale_hemnet_id} to database")
        return True, False  # Success, not already existing
        
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()
        logger.error(f"Error storing sold listing {sale_hemnet_id}: {e}")
        return False, False  # Error, not already existing