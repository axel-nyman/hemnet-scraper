import logging
import os
from datetime import datetime

def setup_logging():
    logger = logging.getLogger('hemnet_scraper')
    
    # Check if the logger has handlers already to avoid duplication
    if logger.hasHandlers():
        return logger

    # Configure logging
    log_directory = os.environ.get('LOG_DIR', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'logs'))

    try:
        os.makedirs(log_directory, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create log directory at {log_directory}: {e}")
        log_directory = os.getcwd()
        print(f"Falling back to current directory for logs: {log_directory}")
        os.makedirs(os.path.join(log_directory, 'logs'), exist_ok=True)
        log_directory = os.path.join(log_directory, 'logs')

    log_filename = f"hemnet_scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_directory, log_filename)

    logger.setLevel(logging.INFO)

    try:
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_path}")
    return logger