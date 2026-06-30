# Header Sync Automation

## Overview

Downloads the latest BSNL DLT Header PDF and converts it into a structured CSV.

## Features

- Downloads latest PDF
- Parses 14k+ pages
- Supports multiline entity names
- Generates CSV
- Logging
- Memory efficient

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```

## Output

```
output/headers.csv
logs/header_sync.log
```