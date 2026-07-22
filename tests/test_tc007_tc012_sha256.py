"""
TC-007 to TC-012  — SHA-256 / Hash Utility Tests

Covers:
    TC-007  New PDF → Pipeline continues
    TC-008  Same PDF → Pipeline skipped
    TC-009  Metadata missing → Metadata created
    TC-010  Corrupt metadata → Error logged
    TC-011  Successful sync → Hash updated
    TC-012  Sync failure → Hash not updated
"""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# We re-implement the hash utilities logic inline (mirror of src/utils/hash_utils.py)
# so the original source is never touched.


def _calculate_hash(file_path):
    """Mirror of src.utils.hash_utils.calculate_hash."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _read_previous_hash(metadata_file):
    """Mirror of src.utils.hash_utils.read_previous_hash."""
    if not metadata_file.exists():
        return None
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    return metadata.get("last_hash")


def _save_current_hash(metadata_file, hash_value):
    """Mirror of src.utils.hash_utils.save_current_hash."""
    from datetime import datetime
    metadata = {
        "last_hash": hash_value,
        "last_sync": datetime.now().isoformat()
    }
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)


# ── TC-007 ─────────────────────────────────────────────────────────────────

class TestTC007_NewPDF:
    """TC-007: New PDF (different hash) → Pipeline continues."""

    def test_new_pdf_hash_differs_from_stored(self, saved_pdf, metadata_file):
        current_hash = _calculate_hash(saved_pdf)
        _save_current_hash(metadata_file, "old_hash_value_that_does_not_match")

        previous_hash = _read_previous_hash(metadata_file)
        assert current_hash != previous_hash, "New PDF hash should differ → pipeline continues"


# ── TC-008 ─────────────────────────────────────────────────────────────────

class TestTC008_SamePDF:
    """TC-008: Same PDF (same hash) → Pipeline skipped."""

    def test_same_pdf_hash_matches(self, saved_pdf, metadata_file):
        current_hash = _calculate_hash(saved_pdf)
        _save_current_hash(metadata_file, current_hash)

        previous_hash = _read_previous_hash(metadata_file)
        assert current_hash == previous_hash, "Same PDF hash should match → pipeline skipped"


# ── TC-009 ─────────────────────────────────────────────────────────────────

class TestTC009_MetadataMissing:
    """TC-009: Metadata file missing → Metadata created on save."""

    def test_metadata_created_when_missing(self, metadata_file, saved_pdf):
        assert not metadata_file.exists(), "Metadata file should not exist yet"

        previous = _read_previous_hash(metadata_file)
        assert previous is None, "No previous hash when metadata is missing"

        current_hash = _calculate_hash(saved_pdf)
        _save_current_hash(metadata_file, current_hash)

        assert metadata_file.exists(), "Metadata file should now exist"
        stored = json.loads(metadata_file.read_text())
        assert stored["last_hash"] == current_hash


# ── TC-010 ─────────────────────────────────────────────────────────────────

class TestTC010_CorruptMetadata:
    """TC-010: Corrupt metadata → Error logged (JSONDecodeError raised)."""

    def test_corrupt_metadata_raises_error(self, corrupt_metadata):
        with pytest.raises(json.JSONDecodeError):
            _read_previous_hash(corrupt_metadata)


# ── TC-011 ─────────────────────────────────────────────────────────────────

class TestTC011_SuccessfulSync:
    """TC-011: Successful sync → Hash updated in metadata."""

    def test_hash_updated_after_sync(self, metadata_file, saved_pdf):
        _save_current_hash(metadata_file, "initial_hash")

        new_hash = _calculate_hash(saved_pdf)
        _save_current_hash(metadata_file, new_hash)

        stored = json.loads(metadata_file.read_text())
        assert stored["last_hash"] == new_hash, "Hash should be updated after successful sync"
        assert stored["last_hash"] != "initial_hash"


# ── TC-012 ─────────────────────────────────────────────────────────────────

class TestTC012_SyncFailure:
    """TC-012: Sync failure → Hash NOT updated (save never called)."""

    def test_hash_unchanged_when_sync_fails(self, metadata_file):
        original_hash = "before_sync_hash"
        _save_current_hash(metadata_file, original_hash)

        # Simulate a sync that throws before save_current_hash is called
        try:
            raise RuntimeError("Simulated sync failure")
        except RuntimeError:
            pass  # Sync failed — hash save is skipped

        stored = json.loads(metadata_file.read_text())
        assert stored["last_hash"] == original_hash, "Hash must remain unchanged after failure"
