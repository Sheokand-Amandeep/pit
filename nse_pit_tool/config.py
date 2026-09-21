
"""Central project settings. Edit this file when you want to change behavior."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / "cache"

NSE_BASE_URL = "https://www.nseindia.com"
PIT_API_PATH = "/api/corporates-pit-gg"

REQUEST_TIMEOUT = 30
XML_WORKERS = 8
MAX_RETRIES = 3

EXCEL_FILENAME = "NSE_PIT_Disclosures.xlsx"
CSV_FILENAME = "NSE_PIT_Disclosures.csv"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/154.0.0.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading",
}
