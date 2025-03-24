# Hemnet Scraper

## Overview

The Hemnet Scraper is a containerized Python application designed to scrape real estate listings from the Hemnet website. It collects data on both active and sold listings and stores this information in a PostgreSQL database. The application uses Playwright for browser automation and BeautifulSoup for HTML parsing.

## Project Structure

The project consists of the following main components:

- **src/**
  - **main.py**: The main entry point for running the scraper.
  - **scrapers/**
    - **active_listings_scraper.py**: Scrapes active listings from Hemnet.
    - **sold_listings_scraper.py**: Scrapes sold listings from Hemnet.
  - **utils/**
    - **database_utils.py**: Contains utility functions for interacting with the PostgreSQL database.
    - **playwright_utils.py**: Provides functions to start and close the Playwright browser.
    - **logging_setup.py**: Configures logging for the application.
- **config/**
  - **.env**: Environment variables for the project.
- **logs/**: Directory for log files.
- **tests/**: Directory for unit tests.
- **notebooks/**: Directory for Jupyter notebooks.
- **.gitignore**: Specifies files and directories to be ignored by Git.
- **README.md**: Documentation for the project.
- **docker-compose.yaml**: Docker configuration for running the application.

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Configuration

Create a `.env` file in the `config` directory with the following variables:

```sh
LOG_DIR=/app/logs
DB_HOST=postgres
DB_NAME=real_estate
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_PORT=5432
```

### Docker Services

The application runs the following containerized services:

- **hemnet_scraper**: Main scraping application
- **postgres**: PostgreSQL database with PostGIS extension
- **jupyter**: Jupyter Lab for data analysis

## Usage

### Starting the Services

```sh
docker-compose up -d
```

### Running the Scraper

```sh
docker-compose up hemnet_scraper
```

### Accessing Services

- **Jupyter Lab**: `http://localhost:8888`
- **PostgreSQL**:
  - Host: `localhost`
  - Port: `5432`
  - Database: `real_estate`
  - Username: `postgres`
  - Password: `yourpassword`

## Monitoring

- Logs are available in the `logs` directory
- Container logs can be viewed using:
  ```sh
  docker-compose logs -f [service_name]
  ```

## Stopping the Services

```sh
docker-compose down
```
