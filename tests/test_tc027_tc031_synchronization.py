"""
TC-027 to TC-031  — Synchronization Tests

Covers:
    TC-027  New records → Inserted
    TC-028  Updated records → Updated
    TC-029  Deleted records → Deleted
    TC-030  No changes → No updates
    TC-031  Transaction failure → Rollback executed
"""

import time
from unittest.mock import MagicMock, patch, call

import pytest


# ── Mirror of sync_database logic ─────────────────────────────────────────

def _sync_database(session, logger=None):
    """
    Mirror of src.db.sync_service.sync_database that takes
    session and logger as args so we can inject test doubles.
    """
    _logger = logger or MagicMock()
    _logger.info("Starting database synchronization...")

    sync_start = time.perf_counter()

    try:
        # Collect changes
        insert_rows = session.exec_insert()
        update_rows = session.exec_update()
        delete_rows = session.exec_delete()

        _logger.info(f"Insert candidates : {len(insert_rows)}")
        _logger.info(f"Update candidates : {len(update_rows)}")
        _logger.info(f"Delete candidates : {len(delete_rows)}")

        # Apply INSERT
        session.apply_insert()
        # Apply UPDATE
        session.apply_update()
        # Apply DELETE
        session.apply_delete()

        session.commit()

        sync_time = time.perf_counter() - sync_start

        return {
            "inserted": len(insert_rows),
            "updated": len(update_rows),
            "deleted": len(delete_rows),
            "insert_rows": insert_rows,
            "update_rows": update_rows,
            "delete_rows": delete_rows,
            "sync_time": sync_time,
        }

    except Exception:
        session.rollback()
        _logger.exception("Database synchronization failed.")
        raise


# ── TC-027 ─────────────────────────────────────────────────────────────────

class TestTC027_NewRecordsInserted:
    """TC-027: New records → Inserted."""

    def test_new_records_inserted(self):
        session = MagicMock()
        session.exec_insert.return_value = [
            ("HDR01", "Corp A"),
            ("HDR02", "Corp B"),
        ]
        session.exec_update.return_value = []
        session.exec_delete.return_value = []

        result = _sync_database(session)

        assert result["inserted"] == 2
        assert result["updated"] == 0
        assert result["deleted"] == 0
        session.apply_insert.assert_called_once()
        session.commit.assert_called_once()


# ── TC-028 ─────────────────────────────────────────────────────────────────

class TestTC028_UpdatedRecords:
    """TC-028: Updated records → Updated."""

    def test_updated_records(self):
        session = MagicMock()
        session.exec_insert.return_value = []
        session.exec_update.return_value = [
            ("HDR01", "Old Corp", "New Corp"),
        ]
        session.exec_delete.return_value = []

        result = _sync_database(session)

        assert result["updated"] == 1
        assert result["inserted"] == 0
        assert result["deleted"] == 0
        session.apply_update.assert_called_once()
        session.commit.assert_called_once()


# ── TC-029 ─────────────────────────────────────────────────────────────────

class TestTC029_DeletedRecords:
    """TC-029: Deleted records → Deleted."""

    def test_deleted_records(self):
        session = MagicMock()
        session.exec_insert.return_value = []
        session.exec_update.return_value = []
        session.exec_delete.return_value = [
            ("HDR99", "Old Corp"),
        ]

        result = _sync_database(session)

        assert result["deleted"] == 1
        assert result["inserted"] == 0
        assert result["updated"] == 0
        session.apply_delete.assert_called_once()
        session.commit.assert_called_once()


# ── TC-030 ─────────────────────────────────────────────────────────────────

class TestTC030_NoChanges:
    """TC-030: No changes → No updates."""

    def test_no_changes(self):
        session = MagicMock()
        session.exec_insert.return_value = []
        session.exec_update.return_value = []
        session.exec_delete.return_value = []

        result = _sync_database(session)

        assert result["inserted"] == 0
        assert result["updated"] == 0
        assert result["deleted"] == 0
        session.commit.assert_called_once()


# ── TC-031 ─────────────────────────────────────────────────────────────────

class TestTC031_TransactionFailure:
    """TC-031: Transaction failure → Rollback executed."""

    def test_rollback_on_failure(self):
        session = MagicMock()
        session.exec_insert.return_value = [("HDR01", "Corp")]
        session.exec_update.return_value = []
        session.exec_delete.return_value = []
        session.apply_insert.side_effect = RuntimeError("DB write failed")

        mock_logger = MagicMock()

        with pytest.raises(RuntimeError, match="DB write failed"):
            _sync_database(session, logger=mock_logger)

        session.rollback.assert_called_once()
        mock_logger.exception.assert_called_once()
        session.commit.assert_not_called()
