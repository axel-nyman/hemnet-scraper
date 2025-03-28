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
- **logs/**: Directory for log files.
- **notebooks/**: Directory for Jupyter notebooks.
- **.gitignore**: Specifies files and directories to be ignored by Git.
- **README.md**: Documentation for the project.
- **docker-compose.yaml**: Docker configuration for running the application.

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Environment Setup

1. Create a `.env` file in the project root:

```bash
cp .env.template .env
```

2. Edit the `.env` file with your credentials and system-specific values:

```properties
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
JUPYTER_TOKEN=your_secure_token_here
UID=your_uid  # Will be different based on your system
GID=your_gid  # Will be different based on your system
```

To get your system's UID and GID values, run these commands in your terminal:

```bash
echo "My UID is: $(id -u)"
echo "My GID is: $(id -g)"
```

Common values:

- macOS: typically UID=501, GID=20
- Linux: typically UID=1000, GID=1000

3. Set proper file permissions:

```bash
chmod 600 .env
```

4. Verify your `.env` file:

```bash
cat .env
```

The output should show all five required environment variables properly set.

### Docker Services

The application runs the following containerized services:

- **hemnet_scraper**: Main scraping application
- **postgres**: PostgreSQL database with PostGIS extension
- **jupyter**: Jupyter Lab for data analysis (password protected)

## Usage

### Starting the Services

```sh
docker-compose up -d
```

### Accessing Services

- **Jupyter Lab**:
  - URL: `http://localhost:8888`
  - Authentication: Required (token specified in .env)
- **PostgreSQL**:
  - Host: `localhost`
  - Port: `5432`
  - Database: `real_estate`
  - Username: from .env (DB_USER)
  - Password: from .env (DB_PASSWORD)

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
