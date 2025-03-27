import schedule
import time
import logging
import argparse
from datetime import datetime
import traceback

# Import your scraper functions
from scrapers.active_listings_scraper import main as scrape_active_listings
from scrapers.sold_listings_scraper import main as scrape_sold_listings
# Import the logging setup function
from utils.logging_setup import setup_logging

# Use the centralized logging setup
logger = setup_logging()
# Rename the logger to be scheduler-specific while still using the central config
logger = logging.getLogger('hemnet_scraper.scheduler')

def run_active_listings_scraper():
    """
    Wrapper function to run the active listings scraper with error handling
    """
    logger.info("Starting active listings scraper")
    try:
        scrape_active_listings()
        logger.info("Active listings scraper completed successfully")
    except Exception as e:
        logger.error(f"Error running active listings scraper: {e}")
        logger.error(traceback.format_exc())
        
def run_sold_listings_scraper():
    """
    Wrapper function to run the sold listings scraper with error handling
    """
    logger.info("Starting sold listings scraper")
    try:
        scrape_sold_listings()
        logger.info("Sold listings scraper completed successfully")
    except Exception as e:
        logger.error(f"Error running sold listings scraper: {e}")
        logger.error(traceback.format_exc())

def run_both_scrapers():
    """
    Run both scrapers in sequence
    """
    logger.info("===== Starting scheduled scraping job =====")
    start_time = datetime.now()
    logger.info(f"Job started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run active listings first
    run_active_listings_scraper()
    
    # Then run sold listings
    run_sold_listings_scraper()
    
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Job completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Total duration: {duration}")
    logger.info("===== Scheduled scraping job completed =====")

def setup_schedule(time_str="02:00", run_now=False):
    """
    Set up the scheduling for both scrapers
    
    Args:
        time_str: Time to run in 24-hour format (default: "02:00")
        run_now: Whether to also run the scrapers immediately
    """
    logger.info(f"Setting up scheduler to run daily at {time_str}")
    
    # Schedule the job to run at the specified time every day
    schedule.every().day.at(time_str).do(run_both_scrapers)
    
    # Run immediately if requested
    if run_now:
        logger.info("Running scrapers immediately")
        run_both_scrapers()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """
    Main function to parse arguments and start the scheduler
    """
    parser = argparse.ArgumentParser(description="Schedule Hemnet scrapers to run daily")
    parser.add_argument(
        "--time", 
        type=str, 
        default="02:00", 
        help="Time to run the scrapers daily (24-hour format, e.g., '02:00')"
    )
    parser.add_argument(
        "--run-now", 
        action="store_true", 
        help="Run the scrapers immediately in addition to scheduling"
    )
    parser.add_argument(
        "--active-only", 
        action="store_true", 
        help="Run only the active listings scraper immediately"
    )
    parser.add_argument(
        "--sold-only", 
        action="store_true", 
        help="Run only the sold listings scraper immediately"
    )
    
    args = parser.parse_args()
    
    # Handle one-time runs without scheduling
    if args.active_only:
        logger.info("Running active listings scraper once")
        run_active_listings_scraper()
        return
    
    if args.sold_only:
        logger.info("Running sold listings scraper once")
        run_sold_listings_scraper()
        return
    
    # Otherwise, set up the scheduler
    setup_schedule(args.time, args.run_now)

if __name__ == "__main__":
    main()