"""
TC-040 to TC-044  — End-to-End Pipeline Tests

Covers:
    TC-040  Complete execution → Pipeline succeeds
    TC-041  Run same PDF twice → Second run skipped
    TC-042  New PDF → Pipeline executes
    TC-043  Import failure → Metadata unchanged
    TC-044  Sync failure → Rollback verified
"""

import csv
import hashlib
import json
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Inline copies of all pipeline components ──────────────────────────────

PURPOSES = {"Promotional", "Transactional/Service"}
CSV_FIELDNAMES = ["S.No", "Header", "Entity Name", "Purpose"]


def calculate_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def read_previous_hash(metadata_file):
    if not metadata_file.exists():
        return None
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    return metadata.get("last_hash")


def save_current_hash(metadata_file, hash_value):
    from datetime import datetime
    metadata = {"last_hash": hash_value, "last_sync": datetime.now().isoformat()}
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)


def parse_page(lines):
    records = []
    state = "SERIAL"
    serial = header = ""
    entity_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line in {
            "List of Headers associated with Principal Entities Registered in DLT",
            "S.No", "Header", "Entity Name", "Purpose",
        }:
            continue

        if state == "SERIAL":
            if re.fullmatch(r"\d+", line):
                serial = line
                state = "HEADER"
            continue
        elif state == "HEADER":
            header = line
            entity_lines = []
            state = "ENTITY"
            continue
        elif state == "ENTITY":
            if line in PURPOSES:
                records.append({
                    "S.No": serial,
                    "Header": header,
                    "Entity Name": " ".join(entity_lines),
                    "Purpose": line,
                })
                state = "SERIAL"
            else:
                entity_lines.append(line)
    return records


def write_records(records, csv_path):
    if not records:
        return
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)


def retry(func, *args, retries=4, initial_delay=0.01,
          backoff_factor=2, exceptions=(Exception,), logger=None, **kwargs):
    _logger = logger or MagicMock()
    delay = initial_delay
    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            _logger.warning(f"{func.__name__} failed (Attempt {attempt}/{retries}) : {e}")
            if attempt == retries:
                _logger.error(f"{func.__name__} failed after {retries} attempts.")
                raise
            _logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= backoff_factor


# ── Simulated pipeline ────────────────────────────────────────────────────

def run_pipeline(
    pdf_path, csv_path, metadata_file,
    page_texts,
    import_fn=None,
    sync_fn=None,
    logger=None,
):
    """
    Full pipeline mirror that accepts all paths and callbacks as arguments.
    """
    _logger = logger or MagicMock()

    _logger.info("Starting Header Sync Job...")

    # Step 1: Skip download (we use pre-written PDF bytes)

    # Step 2: Hash check
    current_hash = calculate_hash(pdf_path)
    previous_hash = read_previous_hash(metadata_file)

    if previous_hash == current_hash:
        _logger.info("PDF has not changed. Skipping synchronization.")
        return {"skipped": True}

    # Remove old CSV
    if csv_path.exists():
        csv_path.unlink()

    total_records = 0

    # Step 3: Parse pages
    for page_text_lines in page_texts:
        records = parse_page(page_text_lines)
        write_records(records, csv_path)
        total_records += len(records)

    _logger.info(f"Records Written : {total_records}")

    # Step 4: Import
    if import_fn:
        retry(import_fn, csv_path, logger=_logger)

    _logger.info("Staging import completed.")

    # Step 5: Sync
    sync_stats = None
    if sync_fn:
        sync_stats = retry(sync_fn, logger=_logger)

    # Step 6: Save hash only after success
    save_current_hash(metadata_file, current_hash)

    _logger.info("Header Sync Job Completed.")

    return {
        "skipped": False,
        "total_records": total_records,
        "sync_stats": sync_stats,
    }


# ── Fixture: create a fake PDF (just bytes for hashing) ───────────────────

@pytest.fixture
def pipeline_env(tmp_path):
    """Set up a clean pipeline environment."""
    pdf_path = tmp_path / "downloads" / "latest_headers.pdf"
    csv_path = tmp_path / "output" / "headers.csv"
    metadata_file = tmp_path / "metadata" / "sync_metadata.json"

    pdf_path.parent.mkdir(parents=True)
    csv_path.parent.mkdir(parents=True)
    metadata_file.parent.mkdir(parents=True)

    # Write a small "PDF" for hashing purposes
    pdf_path.write_bytes(b"FAKE PDF CONTENT FOR HASHING")

    sample_pages = [
        [
            "1", "HDRTST", "Test Corporation", "Promotional",
            "2", "HDRABC", "ABC Pvt Ltd", "Transactional/Service",
        ]
    ]

    return {
        "pdf_path": pdf_path,
        "csv_path": csv_path,
        "metadata_file": metadata_file,
        "sample_pages": sample_pages,
    }


# ── TC-040 ─────────────────────────────────────────────────────────────────

class TestTC040_CompleteExecution:
    """TC-040: Complete execution → Pipeline succeeds."""

    def test_full_pipeline_succeeds(self, pipeline_env):
        result = run_pipeline(
            pdf_path=pipeline_env["pdf_path"],
            csv_path=pipeline_env["csv_path"],
            metadata_file=pipeline_env["metadata_file"],
            page_texts=pipeline_env["sample_pages"],
        )

        assert result["skipped"] is False
        assert result["total_records"] == 2
        assert pipeline_env["csv_path"].exists()
        assert pipeline_env["metadata_file"].exists()

        # Verify CSV content
        with open(pipeline_env["csv_path"], "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["Header"] == "HDRTST"


# ── TC-041 ─────────────────────────────────────────────────────────────────

class TestTC041_SamePDFTwice:
    """TC-041: Run same PDF twice → Second run skipped."""

    def test_second_run_skipped(self, pipeline_env):
        # First run
        result1 = run_pipeline(
            pdf_path=pipeline_env["pdf_path"],
            csv_path=pipeline_env["csv_path"],
            metadata_file=pipeline_env["metadata_file"],
            page_texts=pipeline_env["sample_pages"],
        )
        assert result1["skipped"] is False

        # Second run with same PDF
        result2 = run_pipeline(
            pdf_path=pipeline_env["pdf_path"],
            csv_path=pipeline_env["csv_path"],
            metadata_file=pipeline_env["metadata_file"],
            page_texts=pipeline_env["sample_pages"],
        )
        assert result2["skipped"] is True, "Second run should be skipped (same hash)"


# ── TC-042 ─────────────────────────────────────────────────────────────────

class TestTC042_NewPDFPipeline:
    """TC-042: New PDF (different content) → Pipeline executes."""

    def test_new_pdf_triggers_execution(self, pipeline_env):
        # First run
        run_pipeline(
            pdf_path=pipeline_env["pdf_path"],
            csv_path=pipeline_env["csv_path"],
            metadata_file=pipeline_env["metadata_file"],
            page_texts=pipeline_env["sample_pages"],
        )

        # Change PDF content
        pipeline_env["pdf_path"].write_bytes(b"COMPLETELY DIFFERENT PDF CONTENT")

        # Second run
        result = run_pipeline(
            pdf_path=pipeline_env["pdf_path"],
            csv_path=pipeline_env["csv_path"],
            metadata_file=pipeline_env["metadata_file"],
            page_texts=pipeline_env["sample_pages"],
        )

        assert result["skipped"] is False, "Changed PDF should trigger pipeline"
        assert result["total_records"] == 2


# ── TC-043 ─────────────────────────────────────────────────────────────────

class TestTC043_ImportFailureMetadataUnchanged:
    """TC-043: Import failure → Metadata unchanged."""

    def test_metadata_unchanged_on_import_failure(self, pipeline_env):
        old_hash = "old_hash_before_run"
        save_current_hash(pipeline_env["metadata_file"], old_hash)

        # Change PDF so hash differs
        pipeline_env["pdf_path"].write_bytes(b"NEW PDF CONTENT FOR TC043")

        def failing_import(csv_path):
            raise RuntimeError("Import failed!")

        with pytest.raises(RuntimeError, match="Import failed"):
            run_pipeline(
                pdf_path=pipeline_env["pdf_path"],
                csv_path=pipeline_env["csv_path"],
                metadata_file=pipeline_env["metadata_file"],
                page_texts=pipeline_env["sample_pages"],
                import_fn=failing_import,
            )

        # Metadata should still have the old hash
        stored = json.loads(pipeline_env["metadata_file"].read_text())
        assert stored["last_hash"] == old_hash, "Hash must not update after import failure"


# ── TC-044 ─────────────────────────────────────────────────────────────────

class TestTC044_SyncFailureRollback:
    """TC-044: Sync failure → Rollback verified (hash not updated)."""

    def test_hash_not_updated_on_sync_failure(self, pipeline_env):
        old_hash = "pre_sync_hash"
        save_current_hash(pipeline_env["metadata_file"], old_hash)

        # Change PDF
        pipeline_env["pdf_path"].write_bytes(b"ANOTHER NEW PDF FOR TC044")

        def ok_import(csv_path):
            pass  # import succeeds

        def failing_sync():
            raise RuntimeError("Sync rollback!")

        with pytest.raises(RuntimeError, match="Sync rollback"):
            run_pipeline(
                pdf_path=pipeline_env["pdf_path"],
                csv_path=pipeline_env["csv_path"],
                metadata_file=pipeline_env["metadata_file"],
                page_texts=pipeline_env["sample_pages"],
                import_fn=ok_import,
                sync_fn=failing_sync,
            )

        stored = json.loads(pipeline_env["metadata_file"].read_text())
        assert stored["last_hash"] == old_hash, "Hash must not update after sync failure"
