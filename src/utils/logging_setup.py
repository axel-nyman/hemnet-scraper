import logging
import os
from datetime import datetime
import time

def setup_logging():
    logger = logging.getLogger('hemnet_scraper')
    
    # Check if the logger has handlers already to avoid duplication
    if logger.hasHandlers():
        return logger

    # Configure logging
    # For containers, use LOG_DIR env var
    # For local testing, fallback to a directory relative to the script
    if 'LOG_DIR' in os.environ:
        # Container environment or explicitly set
        log_directory = os.environ['LOG_DIR']
    else:
        # Local testing fallback - create logs in parent directory structure
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up two levels
        log_directory = os.path.join(base_dir, 'logs')

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
        
        # Modified formatter without %(z)s and with timezone info in datefmt
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %Z'
        )
        
        # Use localtime for correct timezone
        formatter.converter = time.localtime
        
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