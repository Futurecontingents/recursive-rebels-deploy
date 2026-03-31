# Recursive Rebels Project 
First clone the repository then do the following steps 

## Prerequisites

- Python **3.11+**
- pip

## Creat a virtual enviroment
py -3.12 -m venv .venv

## Activating it:
### Windows
.venv\Scripts\activate

### macOS / Linux
source .venv/bin/activate

## installing dependencies for scrapper
whilst the VE is active cd into the Web_scrapers_etl_pipline directory
then run the following commands:

- pip install -r requirements.txt
- playwright install chromium

## installing dependencies for backend
whilst the VE is active cd into the Backend directory
then run the following commands:

- pip install flask
- python import_transport_data.py

## Running the backend
whilst the VE is active(and you have previously run python import_transport_data.py) cd into the Backend directory
then run the following command:

python app.py

it will run on: http://127.0.0.1:5000/
if you enter http://127.0.0.1:5000/api/listings in the browser you will see the data in JSON format
if you enter just http://127.0.0.1:5000/ in the browser you will see the frontend map being rendered by the backend(for now it will be blank because we haven't added any data to the database yet)

## Running the scrapper
whilst the VE is active cd into the Web_scrapers_etl_pipline directory
then you can run the following commands:

### Scrape both platforms (default — 5 pages each)
python scraper/run_scraper.py --platform all


### Scrape Bayut only
python scraper/run_scraper.py --platform bayut --max-pages 10


### Scrape PropertyFinder only

python scraper/run_scraper.py --platform propertyfinder --max-pages 3


### Debug mode (visible browser window)

python scraper/run_scraper.py --platform bayut --max-pages 1 --no-headless

## Running the ETL Pipline
whilst the VE is active AND THE BACKEND IS AS WELL cd into the Web_scrapers_etl_pipline directory
then run the following command:

python etl/pipeline.py


now you can open http://127.0.0.1:5000/ on your browser and see the listings with their information pop up on the map


## Recursive Rebels Backend
The scraper sends data to the backend using:

POST /api/listings

Example (JSON body):
{
  "title": "Apartment in Dubai",
  "price": 1500000,
  "latitude": 25.2,
  "longitude": 55.3,
  "source_url": "https://example.com"
}

The backend:
validates the data
generates a fingerprint
prevents duplicates
stores the listing in the database
Frontend → Backend

The frontend retrieves data using:

GET /api/listings
GET /api/listings/ id

The backend:
fetches data from the database
returns structured JSON via DTOs

Data Flow idea:
Scraper  → POST → API → Service → Repository → Database
Frontend → GET  → API → Service → Repository → Database

All interactions go through the API, ensuring consistency and avoiding direct database access.

Running the Backend:
Install dependencies: pip install flask
Download the transit data by running: python import_transport_data.py
Run the server: python app.py
Access the API: http://127.0.0.1:5000/

Notes:
The database is automatically created from database.sql
Duplicate listings are prevented using a fingerprint system
The backend is designed for development use (Flask debug server)



## Scrapper/ETL pipline

```
RecursiveRebels/
├── scraper/
│   ├── base_scraper.py           
│   ├── bayut_scraper.py          
│   ├── propertyfinder_scraper.py
│   ├── propertyfinder/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── parser.py
│   │   └── scraper.py
│   ├── scraper_utils.py         
│   ├── run_scraper.py           
│   └── logs/                   
│
├── etl/
│   ├── extract.py   
│   ├── transform.py  
│   ├── load.py       
│   ├── pipeline.py   
│   └── output/       
│
├── run_outputs/
├── requirements.txt
├── tests/
│   └── test_propertyfinder_parser.py
└── README.md
```

---

## Prerequisites

- Python **3.11+**
- pip

---

## Installation

```bash
git clone <repo-url>
cd RecursiveRebels

# (Recommended) Create and activate a virtual environment
py -3.12 -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Playwright's Chromium browser
playwright install chromium
```

---

## Running the Scrapers

All commands should be run from the **project root** (`RecursiveRebels/`).

### Scrape both platforms (default — 5 pages each)

```bash
python scraper/run_scraper.py --platform all
```

### Scrape Bayut only

```bash
python scraper/run_scraper.py --platform bayut --max-pages 10
```

### Prepare a reusable Bayut session

```bash
python scraper/run_scraper.py --platform bayut --prepare-session --no-headless --save-storage-state run_outputs/bayut_storage_state.json
```

After the browser opens, solve any Bayut challenge manually, return to the terminal, and press Enter to save the session. You can then reuse that session for Bayut scraping:

```bash
python scraper/run_scraper.py --platform bayut --max-pages 3 --storage-state run_outputs/bayut_storage_state.json
```

### Scrape PropertyFinder only

```bash
python scraper/run_scraper.py --platform propertyfinder --max-pages 3
```

The Property Finder scraper reads the page's embedded `__NEXT_DATA__` payload from the Dubai search results and saves one JSON file per scraped page under `run_outputs/`.

### Debug mode (visible browser window)

```bash
python scraper/run_scraper.py --platform bayut --max-pages 1 --no-headless



## Running the ETL Pipeline

After scraping, run the ETL pipeline to clean and export the data:

```bash
python etl/pipeline.py
```

### Custom input / output paths

```bash
python etl/pipeline.py --input run_outputs --output etl/output
```

### Dry run (no CSV files written)

```bash
python etl/pipeline.py --dry-run


# Recursive Rebels Frontend Prototype

This branch contains the frontend prototype for the Recursive Rebels project.

## Current prototype features

- interactive Dubai housing map
- listing markers and popups
- filter panel
- listing details sidebar
- basic accessibility controls
- demo listing data for testing

## File structure

- `map.html` — main prototype page
- `style.css` — layout and styling
- `data.js` — demo listing data
- `ui.js` — filters, sidebar, details, accessibility controls
- `map.js` — map logic, markers, popups, map interaction

## Notes

- the current data is demo data used for frontend testing
- the data structure is based on the current backend/database schema, but it is not final yet
- the frontend will later be connected to backend/API data

## How to run

Open `map.html` directly in the browser, or run a simple local server:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/map.html
```

## Running the app

Inside Backend directory:
```
python app.py
```

Then connect to:
```
http://127.0.0.1:5000/
```
or:
```
http://localhost:5000
```

You can also check the data in API via:
```
http://127.0.0.1:5000/api/listings
```

## Testing

The current frontend prototype was tested manually using demo listing data.

Manual checks included:
- filtering by maximum price
- filtering by minimum transit score
- filtering by maximum distance to nearest transit
- filtering by accessibility features
- marker click updates the details sidebar
- result card click focuses the map on the selected listing
- high contrast toggle changes the visual theme
- larger text toggle increases UI text size