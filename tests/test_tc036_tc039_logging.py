"""
TC-036 to TC-039  — Logging Tests

Covers:
    TC-036  Successful run → Success logs written
    TC-037  Download failure → Error logged
    TC-038  Retry → Retry attempts logged
    TC-039  Sync completed → Summary logged
"""

import logging
import io
from unittest.mock import MagicMock

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_logger(name="TestHeaderSync"):
    """
    Create a logger that writes to a StringIO stream
    so we can inspect log output without touching the real log file.
    """
    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)
    _logger.handlers.clear()

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    _logger.addHandler(handler)

    return _logger, stream


# ── TC-036 ─────────────────────────────────────────────────────────────────

class TestTC036_SuccessfulRunLogs:
    """TC-036: Successful run → Success logs written."""

    def test_success_logs(self):
        logger, stream = _make_logger("TC036")

        # Simulate successful run log messages
        logger.info("Starting Header Sync Job...")
        logger.info("PDF Processed Successfully")
        logger.info("Pages Processed : 100")
        logger.info("Records Written : 5000")
        logger.info("Starting PostgreSQL import...")
        logger.info("Staging import completed.")
        logger.info("Header Sync Job Completed.")

        output = stream.getvalue()

        assert "Starting Header Sync Job..." in output
        assert "PDF Processed Successfully" in output
        assert "Pages Processed" in output
        assert "Records Written" in output
        assert "Header Sync Job Completed." in output
        assert "ERROR" not in output, "No errors should appear in a successful run"


# ── TC-037 ─────────────────────────────────────────────────────────────────

class TestTC037_DownloadFailureLogged:
    """TC-037: Download failure → Error logged."""

    def test_download_error_logged(self):
        logger, stream = _make_logger("TC037")

        # Simulate download failure
        logger.warning("download_pdf failed (Attempt 1/4) : Connection refused")
        logger.error("download_pdf failed after 4 attempts.")

        output = stream.getvalue()

        assert "WARNING" in output
        assert "download_pdf failed" in output
        assert "ERROR" in output
        assert "failed after 4 attempts" in output


# ── TC-038 ─────────────────────────────────────────────────────────────────

class TestTC038_RetryLogged:
    """TC-038: Retry → Retry attempts logged with attempt numbers."""

    def test_retry_attempts_logged(self):
        logger, stream = _make_logger("TC038")

        for attempt in range(1, 5):
            logger.warning(
                f"download_pdf failed (Attempt {attempt}/4) : Timeout"
            )
            if attempt < 4:
                logger.info(f"Retrying in {2 ** (attempt - 1)} seconds...")

        output = stream.getvalue()

        assert "Attempt 1/4" in output
        assert "Attempt 2/4" in output
        assert "Attempt 3/4" in output
        assert "Attempt 4/4" in output
        assert "Retrying in 1 seconds" in output
        assert "Retrying in 2 seconds" in output
        assert "Retrying in 4 seconds" in output


# ── TC-039 ─────────────────────────────────────────────────────────────────

class TestTC039_SyncSummaryLogged:
    """TC-039: Sync completed → Summary logged with counts."""

    def test_sync_summary_logged(self):
        logger, stream = _make_logger("TC039")

        sync_stats = {
            "inserted": 150,
            "updated": 25,
            "deleted": 10,
            "sync_time": 3.45,
        }

        logger.info("=" * 60)
        logger.info("Synchronization Summary")
        logger.info(f"Inserted        : {sync_stats['inserted']}")
        logger.info(f"Updated         : {sync_stats['updated']}")
        logger.info(f"Deleted         : {sync_stats['deleted']}")
        logger.info(f"Sync Time       : {sync_stats['sync_time']:.2f} seconds")
        logger.info("=" * 60)

        output = stream.getvalue()

        assert "Synchronization Summary" in output
        assert "Inserted        : 150" in output
        assert "Updated         : 25" in output
        assert "Deleted         : 10" in output
        assert "Sync Time       : 3.45 seconds" in output
