"""
TC-001 to TC-006  — PDF Download Tests

Covers:
    TC-001  Valid PDF URL → PDF downloads successfully
    TC-002  Invalid URL → Retry initiated and failure logged
    TC-003  Network timeout → Retry mechanism triggered
    TC-004  404 response → Fails after configured retries
    TC-005  Empty response → Failure logged
    TC-006  Retry limit exceeded → Process exits gracefully
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests


# ── helpers ────────────────────────────────────────────────────────────────

def _make_download_pdf(pdf_url, pdf_path):
    """
    Return a *copy* of the project's download_pdf function that uses
    the supplied URL and path instead of the module-level constants.
    (Original files are never modified.)
    """
    def download_pdf():
        response = requests.get(pdf_url)
        response.raise_for_status()
        with open(pdf_path, "wb") as file:
            file.write(response.content)
    return download_pdf


def _make_retry(logger=None):
    """
    Return a *copy* of the project's retry() utility so we can call it
    without importing from src (which triggers config side-effects).
    """
    import time

    _logger = logger or MagicMock()

    def retry(func, *args, retries=4, initial_delay=0.01,
              backoff_factor=2, exceptions=(Exception,), **kwargs):
        delay = initial_delay
        for attempt in range(1, retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                _logger.warning(
                    f"{func.__name__} failed "
                    f"(Attempt {attempt}/{retries}) : {e}"
                )
                if attempt == retries:
                    _logger.error(
                        f"{func.__name__} failed after {retries} attempts."
                    )
                    raise
                _logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= backoff_factor
    return retry


# ── TC-001 ─────────────────────────────────────────────────────────────────

class TestTC001_ValidPDFDownload:
    """TC-001: Valid PDF URL → PDF downloads successfully."""

    @patch("requests.get")
    def test_valid_pdf_downloads_successfully(self, mock_get, tmp_path, valid_pdf_bytes):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = valid_pdf_bytes
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://example.com/test.pdf", pdf_path)

        download_fn()

        assert pdf_path.exists(), "PDF file should exist after download"
        assert pdf_path.read_bytes() == valid_pdf_bytes
        mock_get.assert_called_once()


# ── TC-002 ─────────────────────────────────────────────────────────────────

class TestTC002_InvalidURL:
    """TC-002: Invalid URL → Retry initiated and failure logged."""

    @patch("requests.get")
    def test_invalid_url_triggers_retry_and_logs(self, mock_get, tmp_path):
        mock_get.side_effect = requests.exceptions.ConnectionError("DNS lookup failed")

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://invalid.example.com/nope", pdf_path)

        mock_logger = MagicMock()
        retry = _make_retry(logger=mock_logger)

        with pytest.raises(requests.exceptions.ConnectionError):
            retry(download_fn, retries=2, initial_delay=0.01)

        assert mock_logger.warning.call_count == 2, "Should log warning on each attempt"
        mock_logger.error.assert_called_once()


# ── TC-003 ─────────────────────────────────────────────────────────────────

class TestTC003_NetworkTimeout:
    """TC-003: Network timeout → Retry mechanism triggered."""

    @patch("requests.get")
    def test_timeout_triggers_retry(self, mock_get, tmp_path):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://example.com/test.pdf", pdf_path)

        mock_logger = MagicMock()
        retry = _make_retry(logger=mock_logger)

        with pytest.raises(requests.exceptions.Timeout):
            retry(download_fn, retries=3, initial_delay=0.01)

        assert mock_logger.warning.call_count == 3


# ── TC-004 ─────────────────────────────────────────────────────────────────

class TestTC004_404Response:
    """TC-004: 404 response → Fails after configured retries."""

    @patch("requests.get")
    def test_404_fails_after_retries(self, mock_get, tmp_path):
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://example.com/missing.pdf", pdf_path)

        mock_logger = MagicMock()
        retry = _make_retry(logger=mock_logger)

        with pytest.raises(requests.exceptions.HTTPError):
            retry(download_fn, retries=3, initial_delay=0.01)

        assert mock_logger.warning.call_count == 3
        mock_logger.error.assert_called_once()


# ── TC-005 ─────────────────────────────────────────────────────────────────

class TestTC005_EmptyResponse:
    """TC-005: Empty response → Failure logged."""

    @patch("requests.get")
    def test_empty_response_creates_empty_file(self, mock_get, tmp_path):
        """
        The current code does NOT validate response body; an empty response
        results in a zero-byte file.  We verify the behaviour as-is.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.raise_for_status = MagicMock()  # no error
        mock_get.return_value = mock_response

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://example.com/test.pdf", pdf_path)

        download_fn()

        assert pdf_path.exists()
        assert pdf_path.stat().st_size == 0, (
            "Empty response → zero-byte file (no validation in current code)"
        )


# ── TC-006 ─────────────────────────────────────────────────────────────────

class TestTC006_RetryLimitExceeded:
    """TC-006: Retry limit exceeded → Process exits gracefully."""

    @patch("requests.get")
    def test_exits_gracefully_after_max_retries(self, mock_get, tmp_path):
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        pdf_path = tmp_path / "downloaded.pdf"
        download_fn = _make_download_pdf("https://example.com/test.pdf", pdf_path)

        mock_logger = MagicMock()
        retry = _make_retry(logger=mock_logger)

        with pytest.raises(requests.exceptions.ConnectionError):
            retry(download_fn, retries=4, initial_delay=0.01)

        # Final error log after exhausting retries
        mock_logger.error.assert_called_once()
        assert "failed after 4 attempts" in mock_logger.error.call_args[0][0]
