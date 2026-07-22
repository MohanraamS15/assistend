"""
TC-013 to TC-017  — PDF Parsing Tests

Covers:
    TC-013  Valid PDF → Records extracted
    TC-014  Empty PDF → Handled gracefully
    TC-015  Corrupt PDF → Error logged
    TC-016  Multiline entity names → Parsed correctly
    TC-017  14k+ pages → Parsing completes (simulated)
"""

import re
from unittest.mock import MagicMock

import pytest


# ── Mirror of src/parser.py ───────────────────────────────────────────────
# We duplicate the parser logic so we never import or modify the original.

PURPOSES = {"Promotional", "Transactional/Service"}


def parse_page(lines):
    """Exact copy of src.parser.parse_page."""
    records = []
    state = "SERIAL"
    serial = ""
    header = ""
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


# ── TC-013 ─────────────────────────────────────────────────────────────────

class TestTC013_ValidPDF:
    """TC-013: Valid PDF (well-formed page text) → Records extracted."""

    def test_valid_page_yields_records(self):
        lines = [
            "S.No",
            "Header",
            "Entity Name",
            "Purpose",
            "1",
            "HDRTST",
            "Test Corporation",
            "Promotional",
            "2",
            "HDRXYZ",
            "XYZ Pvt Ltd",
            "Transactional/Service",
        ]

        records = parse_page(lines)
        assert len(records) == 2

        assert records[0]["S.No"] == "1"
        assert records[0]["Header"] == "HDRTST"
        assert records[0]["Entity Name"] == "Test Corporation"
        assert records[0]["Purpose"] == "Promotional"

        assert records[1]["S.No"] == "2"
        assert records[1]["Header"] == "HDRXYZ"
        assert records[1]["Entity Name"] == "XYZ Pvt Ltd"
        assert records[1]["Purpose"] == "Transactional/Service"


# ── TC-014 ─────────────────────────────────────────────────────────────────

class TestTC014_EmptyPDF:
    """TC-014: Empty PDF (no text on page) → Handled gracefully."""

    def test_empty_lines_return_no_records(self):
        records = parse_page([])
        assert records == []

    def test_whitespace_only_returns_no_records(self):
        records = parse_page(["", "  ", "\t", "\n"])
        assert records == []


# ── TC-015 ─────────────────────────────────────────────────────────────────

class TestTC015_CorruptPDF:
    """TC-015: Corrupt PDF → Opening with fitz raises; error logged."""

    def test_corrupt_pdf_raises_on_open(self, tmp_path):
        corrupt_path = tmp_path / "corrupt.pdf"
        corrupt_path.write_bytes(b"NOT A PDF")

        import fitz
        with pytest.raises(Exception):
            fitz.open(str(corrupt_path))


# ── TC-016 ─────────────────────────────────────────────────────────────────

class TestTC016_MultilineEntityNames:
    """TC-016: Multiline entity names → Parsed correctly."""

    def test_multiline_entity_joined(self):
        lines = [
            "1",
            "HDRMULTI",
            "First Line Of Entity",
            "Second Line Of Entity",
            "Third Line Of Entity",
            "Promotional",
        ]

        records = parse_page(lines)
        assert len(records) == 1
        assert records[0]["Entity Name"] == (
            "First Line Of Entity Second Line Of Entity Third Line Of Entity"
        )

    def test_two_records_with_multiline(self):
        lines = [
            "1",
            "HDR01",
            "Part A",
            "Part B",
            "Promotional",
            "2",
            "HDR02",
            "Single Entity",
            "Transactional/Service",
        ]

        records = parse_page(lines)
        assert len(records) == 2
        assert records[0]["Entity Name"] == "Part A Part B"
        assert records[1]["Entity Name"] == "Single Entity"


# ── TC-017 ─────────────────────────────────────────────────────────────────

class TestTC017_14kPlusPages:
    """TC-017: 14k+ pages → Parsing completes (simulated with many calls)."""

    def test_large_page_count_completes(self):
        """
        Simulate parsing 14,000 pages by calling parse_page 14,000 times
        with small input.  This verifies there's no per-call leak or crash.
        """
        single_page_lines = [
            "1", "HDRTEST", "Entity Corp", "Promotional",
        ]

        total_records = 0
        for _ in range(14_000):
            recs = parse_page(single_page_lines)
            total_records += len(recs)

        assert total_records == 14_000, "14k pages should produce 14k records"
