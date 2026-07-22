from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

#DB
DATABASE_URL = os.getenv("DATABASE_URL")

BASE_DIR = Path(__file__).resolve().parent.parent

# URLs
PDF_URL = os.getenv("PDF_URL", "https://www.ucc-bsnl.co.in/header_link_doc/")

# Directories
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

DOWNLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Files
PDF_PATH = DOWNLOAD_DIR / "latest_headers.pdf"
CSV_PATH = OUTPUT_DIR / "headers.csv"
LOG_FILE = LOG_DIR / "header_sync.log"

#Metadata
METADATA_DIR = BASE_DIR / "metadata"
METADATA_DIR.mkdir(exist_ok=True)

METADATA_FILE = METADATA_DIR / "sync_metadata.json"

# Retry Configuration
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "4"))
RETRY_INITIAL_DELAY = int(os.getenv("RETRY_INITIAL_DELAY", "2"))
RETRY_BACKOFF_FACTOR = int(os.getenv("RETRY_BACKOFF_FACTOR", "2"))

# DB Import
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))

