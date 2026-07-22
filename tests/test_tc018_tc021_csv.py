"""
TC-018 to TC-021  — CSV Writer Tests

Covers:
    TC-018  Valid records → CSV generated
    TC-019  Empty records → Handled gracefully
    TC-020  Invalid output path → Error logged
    TC-021  Column validation → Correct headers
"""

import csv
from pathlib import Path

import pytest


# ── Mirror of src/writer.py ───────────────────────────────────────────────

CSV_FIELDNAMES = ["S.No", "Header", "Entity Name", "Purpose"]


def write_records(records, csv_path):
    """
    Mirror of src.writer.write_records but accepts csv_path as an argument
    (instead of using the module-level constant) so we can test with temp files.
    """
    if not records:
        return

    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_FIELDNAMES,
            extrasaction="ignore",
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(records)


# ── TC-018 ─────────────────────────────────────────────────────────────────

class TestTC018_ValidCSV:
    """TC-018: Valid records → CSV generated."""

    def test_csv_generated_with_records(self, tmp_path):
        csv_path = tmp_path / "headers.csv"
        records = [
            {"S.No": "1", "Header": "HDRTST", "Entity Name": "Test Corp", "Purpose": "Promotional"},
            {"S.No": "2", "Header": "HDRABC", "Entity Name": "ABC Ltd", "Purpose": "Transactional/Service"},
        ]

        write_records(records, csv_path)

        assert csv_path.exists(), "CSV file should be created"
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))

        assert len(reader) == 2
        assert reader[0]["Header"] == "HDRTST"
        assert reader[1]["Entity Name"] == "ABC Ltd"

    def test_csv_append_mode(self, tmp_path):
        """Calling write_records twice should append (not overwrite)."""
        csv_path = tmp_path / "headers.csv"
        batch1 = [{"S.No": "1", "Header": "H1", "Entity Name": "E1", "Purpose": "Promotional"}]
        batch2 = [{"S.No": "2", "Header": "H2", "Entity Name": "E2", "Purpose": "Promotional"}]

        write_records(batch1, csv_path)
        write_records(batch2, csv_path)

        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2


# ── TC-019 ─────────────────────────────────────────────────────────────────

class TestTC019_EmptyRecords:
    """TC-019: Empty records → Handled gracefully (no file created)."""

    def test_empty_records_no_file_created(self, tmp_path):
        csv_path = tmp_path / "headers.csv"

        write_records([], csv_path)

        assert not csv_path.exists(), "No file should be created for empty records"

    def test_empty_records_existing_file_unchanged(self, tmp_path):
        csv_path = tmp_path / "headers.csv"
        csv_path.write_text("existing content")
        original = csv_path.read_text()

        write_records([], csv_path)

        assert csv_path.read_text() == original, "Existing file should not be modified"


# ── TC-020 ─────────────────────────────────────────────────────────────────

class TestTC020_InvalidOutputPath:
    """TC-020: Invalid output path → Error logged (raises OSError/PermissionError)."""

    def test_invalid_directory_raises(self, tmp_path):
        # Path with a non-existent parent directory
        bad_path = tmp_path / "nonexistent" / "deep" / "nested" / "headers.csv"
        records = [{"S.No": "1", "Header": "H", "Entity Name": "E", "Purpose": "Promotional"}]

        with pytest.raises((FileNotFoundError, OSError)):
            write_records(records, bad_path)


# ── TC-021 ─────────────────────────────────────────────────────────────────

class TestTC021_ColumnValidation:
    """TC-021: Column validation → Correct headers in CSV."""

    def test_csv_has_correct_headers(self, tmp_path):
        csv_path = tmp_path / "headers.csv"
        records = [{"S.No": "1", "Header": "H", "Entity Name": "E", "Purpose": "Promotional"}]

        write_records(records, csv_path)

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_row = next(reader)

        assert header_row == ["S.No", "Header", "Entity Name", "Purpose"]

    def test_extra_keys_are_ignored(self, tmp_path):
        """Records with extra keys should not add extra columns."""
        csv_path = tmp_path / "headers.csv"
        records = [
            {
                "S.No": "1", "Header": "H", "Entity Name": "E",
                "Purpose": "Promotional", "ExtraField": "ignored",
            }
        ]

        write_records(records, csv_path)

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header_row = next(reader)

        assert "ExtraField" not in header_row
        assert len(header_row) == 4
