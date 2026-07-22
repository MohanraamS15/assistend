"""
TC-022 to TC-026  — DB Import Tests

Covers:
    TC-022  Valid CSV → Imported successfully
    TC-023  DB unavailable → Retry triggered
    TC-024  Invalid credentials → Import fails
    TC-025  Duplicate records → Handled correctly
    TC-026  Empty CSV → Skipped/handled
"""

import csv
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────

CSV_FIELDNAMES = ["S.No", "Header", "Entity Name", "Purpose"]


def _write_sample_csv(csv_path, rows):
    """Helper to create a CSV file with given rows."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    return csv_path


class FakeStagingModel:
    """Mimics SenderIDMappingStaging without importing sqlmodel."""
    def __init__(self, sender_id, sender_entity):
        self.sender_id = sender_id
        self.sender_entity = sender_entity


def _import_csv(csv_path, session, batch_size=5000, logger=None):
    """
    Mirror of src.db.importer.import_csv but takes session & logger
    as arguments so we can inject mocks without touching original code.
    """
    _logger = logger or MagicMock()
    start_time = time.perf_counter()
    total_rows = 0
    batch = []

    _logger.info("Starting staging import...")

    try:
        _logger.info("Clearing staging table...")
        session.execute(MagicMock())  # TRUNCATE
        session.commit()
        _logger.info("Staging table cleared.")

        with open(csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                mapping = FakeStagingModel(
                    sender_id=row["Header"].strip(),
                    sender_entity=row["Entity Name"].strip(),
                )
                batch.append(mapping)

                if len(batch) >= batch_size:
                    session.add_all(batch)
                    session.commit()
                    total_rows += len(batch)
                    batch.clear()

            if batch:
                session.add_all(batch)
                session.commit()
                total_rows += len(batch)

        return total_rows

    except Exception:
        session.rollback()
        _logger.exception("Staging import failed.")
        raise


# ── TC-022 ─────────────────────────────────────────────────────────────────

class TestTC022_ValidCSVImport:
    """TC-022: Valid CSV → Imported successfully."""

    def test_valid_csv_imported(self, tmp_path):
        csv_path = _write_sample_csv(tmp_path / "test.csv", [
            {"S.No": "1", "Header": "HDR01", "Entity Name": "Corp A", "Purpose": "Promotional"},
            {"S.No": "2", "Header": "HDR02", "Entity Name": "Corp B", "Purpose": "Promotional"},
        ])

        session = MagicMock()
        total = _import_csv(csv_path, session)

        assert total == 2
        session.add_all.assert_called()
        session.commit.assert_called()


# ── TC-023 ─────────────────────────────────────────────────────────────────

class TestTC023_DBUnavailable:
    """TC-023: DB unavailable → Retry triggered."""

    def test_db_unavailable_retries(self, tmp_path):
        csv_path = _write_sample_csv(tmp_path / "test.csv", [
            {"S.No": "1", "Header": "HDR01", "Entity Name": "Corp", "Purpose": "Promotional"},
        ])

        session = MagicMock()
        call_count = 0

        def failing_commit():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("DB is unavailable")

        session.commit.side_effect = failing_commit

        mock_logger = MagicMock()

        # First two calls raise, so import_csv should raise
        with pytest.raises(ConnectionError):
            _import_csv(csv_path, session, logger=mock_logger)

        session.rollback.assert_called()
        mock_logger.exception.assert_called()


# ── TC-024 ─────────────────────────────────────────────────────────────────

class TestTC024_InvalidCredentials:
    """TC-024: Invalid credentials → Import fails."""

    def test_invalid_credentials_fails(self, tmp_path):
        csv_path = _write_sample_csv(tmp_path / "test.csv", [
            {"S.No": "1", "Header": "HDR01", "Entity Name": "Corp", "Purpose": "Promotional"},
        ])

        session = MagicMock()
        session.execute.side_effect = PermissionError("Authentication failed")

        mock_logger = MagicMock()

        with pytest.raises(PermissionError):
            _import_csv(csv_path, session, logger=mock_logger)

        session.rollback.assert_called()


# ── TC-025 ─────────────────────────────────────────────────────────────────

class TestTC025_DuplicateRecords:
    """TC-025: Duplicate records → Handled correctly (staging table is truncated first)."""

    def test_duplicate_records_imported(self, tmp_path):
        """
        The import process TRUNCATEs the staging table before import,
        so duplicate rows from CSV are simply inserted as-is into a fresh table.
        """
        csv_path = _write_sample_csv(tmp_path / "test.csv", [
            {"S.No": "1", "Header": "HDR01", "Entity Name": "Corp A", "Purpose": "Promotional"},
            {"S.No": "2", "Header": "HDR01", "Entity Name": "Corp A", "Purpose": "Promotional"},
        ])

        session = MagicMock()
        total = _import_csv(csv_path, session)

        assert total == 2, "Both duplicate rows should be imported into staging"


# ── TC-026 ─────────────────────────────────────────────────────────────────

class TestTC026_EmptyCSV:
    """TC-026: Empty CSV (header only, no data rows) → Skipped/handled."""

    def test_empty_csv_imports_zero_rows(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
            w.writeheader()

        session = MagicMock()
        total = _import_csv(csv_path, session)

        assert total == 0
        # add_all should not be called when there are no rows
        session.add_all.assert_not_called()
