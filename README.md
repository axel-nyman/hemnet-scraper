# Hemnet Scraper

## Overview

The Hemnet Scraper is a Python application designed to scrape real estate listings from the Hemnet website. It collects data on both active and sold listings and stores this information in a PostgreSQL database. The application uses Playwright for browser automation and BeautifulSoup for HTML parsing.

## Project Structure

The project consists of the following main components:

- **scheduler.py**: Manages the scheduling of scraping tasks.
- **database_utils.py**: Contains utility functions for interacting with the PostgreSQL database.
- **playwright_utils.py**: Provides functions to start and close the Playwright browser.
- **logging_setup.py**: Configures logging for the application.
- **active_listings_scraper.py**: Scrapes active listings from Hemnet.
- **sold_listings_scraper.py**: Scrapes sold listings from Hemnet.
- **main.py**: The main entry point for running the scraper manually.
- **.gitignore**: Specifies files and directories to be ignored by Git.
- **README.md**: Documentation for the project.

## Installation

1. **Clone the repository**:

   ```sh
   git clone <repository_url>
   cd hemnet-scraper
   ```

2. **Create a virtual environment**:

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:

   ```sh
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file in the project root and add the following variables:
   ```sh
   LOG_DIR=<path_to_log_directory>
   ```

## Usage

### Running the Scraper

To run the scraper manually, execute the `main.py` script:

```sh
python main.py
```
