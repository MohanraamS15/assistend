# DLT Header Sync Automation

## Overview

DLT Header Sync Automation is a Python-based backend automation tool that downloads the latest BSNL DLT Header PDF, extracts and parses all Sender ID mappings, imports them into a PostgreSQL staging table, synchronizes the master table, and generates a synchronization report.

The pipeline is designed to be reliable, idempotent, and production-ready by avoiding unnecessary processing and automatically retrying transient failures.

---

## Features

- Downloads the latest BSNL DLT Header PDF
- Parses 14,000+ PDF pages efficiently
- Supports multiline entity names
- Generates structured CSV output
- Imports data into PostgreSQL staging table
- Synchronizes staging data with the master table
- Generates synchronization reports
- SHA-256 based PDF change detection
- Generic retry mechanism with exponential backoff
- Structured logging
- Transaction-safe database synchronization
- Idempotent execution (skips processing when the source PDF is unchanged)
- Comprehensive test suite covering 44 test cases (using pytest)
- Environment-based configuration via `.env` file

---

## Workflow

```text
Download Latest PDF
        │
        ▼
Calculate SHA-256 Hash
        │
        ▼
PDF Changed?
   ┌────────────┐
   │     No     │
   │    Exit    │
   └────────────┘
        │ Yes
        ▼
Parse PDF
        │
        ▼
Generate CSV
        │
        ▼
Import into PostgreSQL Staging
        │
        ▼
Synchronize Master Table
        │
        ▼
Generate Report
        │
        ▼
Save Latest Hash
```

---

## Project Structure

```
.
├── .env                  # Environment configuration
├── downloads/
├── logs/
├── metadata/
├── output/
├── reports/
├── src/
│   ├── db/
│   ├── utils/
│   ├── downloader.py
│   ├── extractor.py
│   ├── parser.py
│   ├── writer.py
│   ├── main.py
│   └── ...
├── tests/                # Test suite
├── requirements.txt
└── README.md
```

---

## Tech Stack

- Python 3.x
- PostgreSQL
- SQLModel
- PyMuPDF (fitz)
- Requests
- CSV
- hashlib (SHA-256)
- Logging

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Configuration

The project uses environment variables for configuration. Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql://postgres:1234@localhost:5432/senderid_mapping
PDF_URL=https://www.ucc-bsnl.co.in/header_link_doc/
RETRY_COUNT=4
RETRY_INITIAL_DELAY=2
RETRY_BACKOFF_FACTOR=2
BATCH_SIZE=5000
```

---

## Run

```bash
python -m src.main
```

---

## Testing

The project includes a comprehensive test suite covering 44 test cases (download, parsing, database, retry logic, etc.).

To run the tests:

```bash
pytest tests/ -v
```

---

## Output

```
output/headers.csv
reports/
logs/header_sync.log
metadata/sync_metadata.json
```

---

## Reliability Features

- **SHA-256 Change Detection**
  - Skips the entire pipeline when the downloaded PDF has not changed.

- **Retry Mechanism**
  - Automatically retries transient failures using exponential backoff.

- **Transaction Safety**
  - Database synchronization is executed within transactions to prevent partial updates.

- **Structured Logging**
  - Records detailed execution logs for monitoring and troubleshooting.

---

## Future Enhancements

- Email/Slack notifications
- Archive processed PDFs
- Execution metrics dashboard
- Cron-based scheduled execution