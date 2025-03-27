-- Drop existing schema if needed (commented out for safety)
-- DROP SCHEMA IF EXISTS real_estate CASCADE;

-- Create schema
CREATE SCHEMA real_estate;

-- Create lookup tables first
CREATE TABLE "housing_form_types" (
    "housing_form_id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "tenure_types" (
    "tenure_id" SERIAL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "energy_classifications" (
    "energy_classification_id" SERIAL PRIMARY KEY,
    "classification" VARCHAR(50) NOT NULL UNIQUE,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "brokers" (
    "broker_id" BIGSERIAL PRIMARY KEY,
    "broker_hemnet_id" BIGINT NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255),
    "phone" VARCHAR(50),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "broker_agencies" (
    "agency_id" BIGSERIAL PRIMARY KEY,
    "agency_hemnet_id" BIGINT NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "website" VARCHAR(255),
    "logo_url" VARCHAR(255),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "broker_agency_relationships" (
    "broker_id" BIGINT NOT NULL,
    "agency_id" BIGINT NOT NULL,
    "start_date" DATE NOT NULL DEFAULT CURRENT_DATE,
    "end_date" DATE,
    "is_active" BOOLEAN DEFAULT TRUE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("broker_id", "agency_id", "start_date"),
    CONSTRAINT "broker_agency_relationships_broker_id_fkey" FOREIGN KEY ("broker_id") 
        REFERENCES "brokers" ("broker_id") ON DELETE CASCADE,
    CONSTRAINT "broker_agency_relationships_agency_id_fkey" FOREIGN KEY ("agency_id") 
        REFERENCES "broker_agencies" ("agency_id") ON DELETE CASCADE
);

CREATE TABLE "housing_cooperatives" (
    "housing_cooperative_id" SERIAL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "org_number" VARCHAR(100),
    "foundation_year" INTEGER,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "locations" (
    "location_id" BIGSERIAL PRIMARY KEY,
    "location_hemnet_id" BIGINT NOT NULL UNIQUE,
    "location_name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(255),
    "parent_location_id" BIGINT,
    "latitude" DECIMAL(10, 8),
    "longitude" DECIMAL(11, 8),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "locations_parent_location_id_fkey" FOREIGN KEY ("parent_location_id") 
        REFERENCES "locations" ("location_id") ON DELETE SET NULL
);

CREATE TABLE "amenities" (
    "amenity_id" BIGSERIAL PRIMARY KEY,
    "amenity_name" VARCHAR(255) NOT NULL UNIQUE,
    "category" VARCHAR(100),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "listings" (
    "listing_id" BIGSERIAL PRIMARY KEY,
    "listing_hemnet_id" BIGINT NOT NULL UNIQUE,
    "url" VARCHAR(255) NOT NULL UNIQUE,
    "street_address" VARCHAR(255) NOT NULL,
    "postcode" VARCHAR(20),
    "tenure_id" INTEGER NOT NULL,
    "number_of_rooms" DECIMAL(4, 1),
    "asking_price" DECIMAL(15, 2) NOT NULL,
    "squaremeter_price" DECIMAL(15, 2),
    "fee" DECIMAL(10, 2),
    "yearly_arrendee_fee" DECIMAL(10, 2),
    "yearly_leasehold_fee" DECIMAL(10, 2),
    "running_costs" DECIMAL(10, 2),
    "construction_year" INTEGER CHECK (construction_year > 1500 AND construction_year <= EXTRACT(YEAR FROM CURRENT_DATE)),
    "living_area" DECIMAL(10, 2),
    "is_foreclosure" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_new_construction" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_project" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_upcoming" BOOLEAN NOT NULL DEFAULT FALSE,
    "supplemental_area" DECIMAL(10, 2),
    "land_area" DECIMAL(12, 2),
    "housing_form_id" INTEGER NOT NULL,
    "housing_cooperative_id" INTEGER,
    "energy_classification_id" INTEGER,
    "floor" INTEGER,
    "published_date" DATE NOT NULL,
    "status" VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'sold', 'removed', 'expired')),
    "broker_id" BIGINT NOT NULL,
    "closest_water_distance_meters" INTEGER,
    "coastline_distance_meters" INTEGER,
    "latitude" DECIMAL(10, 8),
    "longitude" DECIMAL(11, 8),
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "listings_tenure_id_fkey" FOREIGN KEY ("tenure_id") 
        REFERENCES "tenure_types" ("tenure_id") ON DELETE RESTRICT,
    CONSTRAINT "listings_housing_form_id_fkey" FOREIGN KEY ("housing_form_id") 
        REFERENCES "housing_form_types" ("housing_form_id") ON DELETE RESTRICT,
    CONSTRAINT "listings_housing_cooperative_id_fkey" FOREIGN KEY ("housing_cooperative_id") 
        REFERENCES "housing_cooperatives" ("housing_cooperative_id") ON DELETE SET NULL,
    CONSTRAINT "listings_energy_classification_id_fkey" FOREIGN KEY ("energy_classification_id") 
        REFERENCES "energy_classifications" ("energy_classification_id") ON DELETE SET NULL,
    CONSTRAINT "listings_broker_id_fkey" FOREIGN KEY ("broker_id") 
        REFERENCES "brokers" ("broker_id") ON DELETE RESTRICT,
    CONSTRAINT "listing_price_check" CHECK (asking_price >= 0),
    CONSTRAINT "listing_area_check" CHECK (living_area >= 0),
    CONSTRAINT "listing_land_area_check" CHECK (land_area >= 0)
);

CREATE TABLE "property_sales" (
    "sale_id" BIGSERIAL PRIMARY KEY,
    "sale_hemnet_id" BIGINT NOT NULL UNIQUE,
    "listing_id" BIGINT,  -- Can be NULL if we don't have the original listing
    "listing_hemnet_id" BIGINT NOT NULL,  -- original_hemnet_id from the scraper
    "final_price" DECIMAL(15, 2) NOT NULL,
    "asking_price" DECIMAL(15, 2),  -- Could be different from the original listing
    "price_change" DECIMAL(15, 2),  -- Difference between asking and final
    "price_change_percentage" DECIMAL(8, 2),
    "sale_date" DATE NOT NULL,
    "sale_date_str" VARCHAR(50),  -- Original string format from scraped data
    "broker_agency" VARCHAR(255),
    "living_area" DECIMAL(10, 2),
    "land_area" DECIMAL(12, 2),
    "number_of_rooms" DECIMAL(4, 1),
    "construction_year" INTEGER,
    "street_address" VARCHAR(255),
    "area" VARCHAR(255),
    "municipality" VARCHAR(255),
    "running_costs" DECIMAL(10, 2),
    "url" VARCHAR(255) NOT NULL UNIQUE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "property_sales_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE SET NULL,
    CONSTRAINT "property_sales_price_check" CHECK (final_price >= 0)
);

CREATE TABLE "listing_amenities" (
    "listing_id" BIGINT NOT NULL,
    "amenity_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("listing_id", "amenity_id"),
    CONSTRAINT "listing_amenities_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE CASCADE,
    CONSTRAINT "listing_amenities_amenity_id_fkey" FOREIGN KEY ("amenity_id") 
        REFERENCES "amenities" ("amenity_id") ON DELETE CASCADE
);

CREATE TABLE "listing_locations" (
    "listing_id" BIGINT NOT NULL,
    "location_id" BIGINT NOT NULL,
    "distance_km" DECIMAL(10, 2),
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("listing_id", "location_id"),
    CONSTRAINT "listing_locations_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE CASCADE,
    CONSTRAINT "listing_locations_location_id_fkey" FOREIGN KEY ("location_id") 
        REFERENCES "locations" ("location_id") ON DELETE CASCADE
);

CREATE TABLE "listing_agencies" (
    "listing_id" BIGINT NOT NULL,
    "agency_id" BIGINT NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("listing_id", "agency_id"),
    CONSTRAINT "listing_agencies_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE CASCADE,
    CONSTRAINT "listing_agencies_agency_id_fkey" FOREIGN KEY ("agency_id") 
        REFERENCES "broker_agencies" ("agency_id") ON DELETE CASCADE
);

CREATE TABLE "listing_images" (
    "image_id" BIGSERIAL PRIMARY KEY,
    "listing_id" BIGINT NOT NULL,
    "url" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "display_order" INTEGER NOT NULL DEFAULT 0,
    "is_primary" BOOLEAN DEFAULT FALSE,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "listing_images_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE CASCADE
);

CREATE TABLE "listing_viewings" (
    "viewing_id" BIGSERIAL PRIMARY KEY,
    "listing_id" BIGINT NOT NULL,
    "start_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "end_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "description" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "listing_viewings_listing_id_fkey" FOREIGN KEY ("listing_id") 
        REFERENCES "listings" ("listing_id") ON DELETE CASCADE,
    CONSTRAINT "listing_viewings_time_check" CHECK (end_time > start_time)
);

-- Create indexes for the listings table
CREATE INDEX "idx_listings_broker_id" ON "listings" ("broker_id");
CREATE INDEX "idx_listings_housing_form_id" ON "listings" ("housing_form_id");
CREATE INDEX "idx_listings_tenure_id" ON "listings" ("tenure_id");
CREATE INDEX "idx_listings_housing_cooperative_id" ON "listings" ("housing_cooperative_id");
CREATE INDEX "idx_listings_energy_classification_id" ON "listings" ("energy_classification_id");
CREATE INDEX "idx_listings_asking_price" ON "listings" ("asking_price");
CREATE INDEX "idx_listings_living_area" ON "listings" ("living_area");
CREATE INDEX "idx_listings_postcode" ON "listings" ("postcode");
CREATE INDEX "idx_listings_published_date" ON "listings" ("published_date");
CREATE INDEX "idx_listings_status" ON "listings" ("status");

-- Standard indexes for location data
CREATE INDEX "idx_listings_location" ON "listings" ("longitude", "latitude")
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create indexes for the property_sales table
CREATE INDEX "idx_property_sales_listing_id" ON "property_sales" ("listing_id");
CREATE INDEX "idx_property_sales_listing_hemnet_id" ON "property_sales" ("listing_hemnet_id");
CREATE INDEX "idx_property_sales_sale_date" ON "property_sales" ("sale_date");
CREATE INDEX "idx_property_sales_final_price" ON "property_sales" ("final_price");
CREATE INDEX "idx_property_sales_broker_agency" ON "property_sales" ("broker_agency");

-- Standard index for locations
CREATE INDEX "idx_locations_location" ON "locations" ("longitude", "latitude")
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create index for housing_cooperatives
CREATE INDEX "idx_housing_cooperatives_name" ON "housing_cooperatives" ("name");

-- Add triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for all tables with updated_at column
CREATE TRIGGER update_listings_timestamp BEFORE UPDATE ON "listings" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_property_sales_timestamp BEFORE UPDATE ON "property_sales" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_brokers_timestamp BEFORE UPDATE ON "brokers" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_broker_agencies_timestamp BEFORE UPDATE ON "broker_agencies" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_locations_timestamp BEFORE UPDATE ON "locations" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_amenities_timestamp BEFORE UPDATE ON "amenities" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_housing_form_types_timestamp BEFORE UPDATE ON "housing_form_types" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_tenure_types_timestamp BEFORE UPDATE ON "tenure_types" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_energy_classifications_timestamp BEFORE UPDATE ON "energy_classifications" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_listing_images_timestamp BEFORE UPDATE ON "listing_images" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_listing_viewings_timestamp BEFORE UPDATE ON "listing_viewings" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_broker_agency_relationships_timestamp BEFORE UPDATE ON "broker_agency_relationships" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();
CREATE TRIGGER update_housing_cooperatives_timestamp BEFORE UPDATE ON "housing_cooperatives" FOR EACH ROW EXECUTE PROCEDURE update_timestamp();

-- Create views for easier data analysis

-- View to join listings with their sales data
CREATE VIEW "listing_sales_view" AS
SELECT 
    l.listing_id,
    l.listing_hemnet_id,
    l.street_address,
    l.postcode,
    l.asking_price AS original_asking_price,
    l.published_date,
    ps.sale_id,
    ps.sale_hemnet_id,
    ps.final_price,
    ps.sale_date,
    ps.price_change,
    ps.price_change_percentage,
    (ps.final_price - l.asking_price) AS price_difference,
    CASE 
        WHEN l.asking_price > 0 THEN 
            ((ps.final_price - l.asking_price) / l.asking_price * 100)
        ELSE NULL
    END AS price_difference_percentage,
    l.living_area,
    CASE 
        WHEN l.living_area > 0 THEN 
            (ps.final_price / l.living_area)
        ELSE NULL
    END AS final_price_per_sqm,
    l.broker_id,
    b.name AS broker_name,
    ps.broker_agency,
    l.housing_form_id,
    hft.name AS housing_form_name,
    l.tenure_id,
    tt.name AS tenure_name,
    l.housing_cooperative_id,
    hc.name AS housing_cooperative_name,
    (ps.sale_date - l.published_date) AS days_on_market
FROM 
    "listings" l
JOIN 
    "property_sales" ps ON l.listing_id = ps.listing_id
LEFT JOIN 
    "brokers" b ON l.broker_id = b.broker_id
LEFT JOIN 
    "housing_form_types" hft ON l.housing_form_id = hft.housing_form_id
LEFT JOIN 
    "tenure_types" tt ON l.tenure_id = tt.tenure_id
LEFT JOIN
    "housing_cooperatives" hc ON l.housing_cooperative_id = hc.housing_cooperative_id;

-- View for unmatched sales (sold listings we don't have the original listing for)
CREATE VIEW "unmatched_sales_view" AS
SELECT 
    ps.sale_id,
    ps.sale_hemnet_id,
    ps.listing_hemnet_id,
    ps.final_price,
    ps.asking_price,
    ps.price_change,
    ps.price_change_percentage,
    ps.sale_date,
    ps.broker_agency,
    ps.living_area,
    ps.land_area,
    ps.number_of_rooms,
    ps.construction_year,
    ps.street_address,
    ps.area,
    ps.municipality,
    ps.running_costs,
    ps.url
FROM 
    "property_sales" ps
WHERE 
    ps.listing_id IS NULL;

-- View for market performance by location
CREATE VIEW "location_market_performance" AS
SELECT 
    loc.location_id,
    loc.location_name,
    loc.type,
    COUNT(DISTINCT l.listing_id) AS total_listings,
    COUNT(DISTINCT ps.sale_id) AS total_sales,
    ROUND(AVG(ps.final_price), 2) AS avg_final_price,
    ROUND(AVG(ps.price_change_percentage), 2) AS avg_price_change_percentage,
    ROUND(AVG(ps.sale_date - l.published_date), 1) AS avg_days_on_market,
    ROUND(AVG(CASE WHEN l.living_area > 0 THEN ps.final_price / l.living_area ELSE NULL END), 2) AS avg_price_per_sqm
FROM 
    "locations" loc
JOIN 
    "listing_locations" ll ON loc.location_id = ll.location_id
JOIN 
    "listings" l ON ll.listing_id = l.listing_id
LEFT JOIN 
    "property_sales" ps ON l.listing_id = ps.listing_id
WHERE 
    ps.sale_id IS NOT NULL
GROUP BY 
    loc.location_id, loc.location_name, loc.type;

-- View for housing cooperative performance
CREATE VIEW "housing_cooperative_performance" AS
SELECT
    hc.housing_cooperative_id,
    hc.name AS housing_cooperative_name,
    COUNT(DISTINCT l.listing_id) AS total_listings,
    COUNT(DISTINCT ps.sale_id) AS total_sales,
    ROUND(AVG(l.asking_price), 2) AS avg_asking_price,
    ROUND(AVG(ps.final_price), 2) AS avg_final_price,
    ROUND(AVG(l.squaremeter_price), 2) AS avg_sqm_price_asking,
    ROUND(AVG(CASE WHEN l.living_area > 0 THEN ps.final_price / l.living_area ELSE NULL END), 2) AS avg_sqm_price_final,
    ROUND(AVG(l.fee), 2) AS avg_monthly_fee,
    ROUND(AVG(ps.price_change_percentage), 2) AS avg_price_change_percentage,
    ROUND(AVG(ps.sale_date - l.published_date), 1) AS avg_days_on_market
FROM
    "housing_cooperatives" hc
JOIN
    "listings" l ON hc.housing_cooperative_id = l.housing_cooperative_id
LEFT JOIN
    "property_sales" ps ON l.listing_id = ps.listing_id
GROUP BY
    hc.housing_cooperative_id, hc.name;