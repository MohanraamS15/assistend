"""
conftest.py — Shared fixtures for all DLT Header Sync Automation tests.

This file provides reusable pytest fixtures (temporary dirs, fake PDFs,
sample CSV data, mock DB sessions, etc.) so individual test modules
stay focused on their own scenarios.
"""

import csv
import json
import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Temporary directory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir(tmp_path):
    """Return a clean temporary directory as a Path."""
    return tmp_path


@pytest.fixture
def downloads_dir(tmp_dir):
    d = tmp_dir / "downloads"
    d.mkdir()
    return d


@pytest.fixture
def output_dir(tmp_dir):
    d = tmp_dir / "output"
    d.mkdir()
    return d


@pytest.fixture
def metadata_dir(tmp_dir):
    d = tmp_dir / "metadata"
    d.mkdir()
    return d


@pytest.fixture
def logs_dir(tmp_dir):
    d = tmp_dir / "logs"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# PDF fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_pdf_bytes():
    """Minimal valid PDF (1-page, blank)."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )


@pytest.fixture
def corrupt_pdf_bytes():
    """Not a valid PDF at all."""
    return b"THIS IS NOT A PDF FILE AT ALL"


@pytest.fixture
def empty_pdf_bytes():
    """An empty file (zero bytes)."""
    return b""


@pytest.fixture
def saved_pdf(downloads_dir, valid_pdf_bytes):
    """Write a minimal valid PDF to disk and return its path."""
    pdf_path = downloads_dir / "latest_headers.pdf"
    pdf_path.write_bytes(valid_pdf_bytes)
    return pdf_path


# ---------------------------------------------------------------------------
# CSV fixtures
# ---------------------------------------------------------------------------

SAMPLE_RECORDS = [
    {"S.No": "1", "Header": "HDRTST", "Entity Name": "Test Corp", "Purpose": "Promotional"},
    {"S.No": "2", "Header": "HDRABC", "Entity Name": "ABC Ltd", "Purpose": "Transactional/Service"},
]

CSV_FIELDNAMES = ["S.No", "Header", "Entity Name", "Purpose"]


@pytest.fixture
def sample_records():
    return list(SAMPLE_RECORDS)


@pytest.fixture
def sample_csv(output_dir):
    """Write a small sample CSV and return its path."""
    csv_path = output_dir / "headers.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        w.writerows(SAMPLE_RECORDS)
    return csv_path


@pytest.fixture
def empty_csv(output_dir):
    """CSV with only the header row (no data rows)."""
    csv_path = output_dir / "headers_empty.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
    return csv_path


# ---------------------------------------------------------------------------
# Metadata / hash fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def metadata_file(metadata_dir):
    """Return the path to a (not-yet-existing) metadata file."""
    return metadata_dir / "sync_metadata.json"


@pytest.fixture
def metadata_with_hash(metadata_file):
    """Write a known hash into the metadata file."""
    data = {"last_hash": "abc123", "last_sync": "2026-01-01T00:00:00"}
    metadata_file.write_text(json.dumps(data))
    return metadata_file


@pytest.fixture
def corrupt_metadata(metadata_file):
    """Write invalid JSON to the metadata file."""
    metadata_file.write_text("NOT VALID JSON {{{")
    return metadata_file


# ---------------------------------------------------------------------------
# Mock DB session fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    """Return a MagicMock that behaves like a SQLModel/SQLAlchemy Session."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session
