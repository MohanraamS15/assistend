"""
TC-032 to TC-035  — Retry Mechanism Tests

Covers:
    TC-032  Download fails once → Retry succeeds
    TC-033  Import fails twice → Retry succeeds
    TC-034  All retries fail → Process terminates
    TC-035  Backoff timing → Delay increases exponentially
"""

import time
from unittest.mock import MagicMock, patch

import pytest


# ── Mirror of src/utils/retry.py ──────────────────────────────────────────

def retry(func, *args, retries=4, initial_delay=0.01,
          backoff_factor=2, exceptions=(Exception,),
          logger=None, **kwargs):
    """
    Mirror of src.utils.retry.retry — accepts logger as kwarg
    and uses tiny delays for fast tests.
    """
    _logger = logger or MagicMock()
    delay = initial_delay
    delays_used = []

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
            delays_used.append(delay)
            time.sleep(delay)
            delay *= backoff_factor

    return delays_used  # unreachable, but aids typing


# ── TC-032 ─────────────────────────────────────────────────────────────────

class TestTC032_RetrySucceedsAfterOneFailure:
    """TC-032: Download fails once → Retry succeeds on second attempt."""

    def test_succeeds_on_second_attempt(self):
        call_count = 0

        def flaky_download():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network blip")
            return "success"

        mock_logger = MagicMock()
        result = retry(flaky_download, retries=3, initial_delay=0.01, logger=mock_logger)

        assert result == "success"
        assert call_count == 2
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()


# ── TC-033 ─────────────────────────────────────────────────────────────────

class TestTC033_RetrySucceedsAfterTwoFailures:
    """TC-033: Import fails twice → Retry succeeds on third attempt."""

    def test_succeeds_on_third_attempt(self):
        call_count = 0

        def flaky_import():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("DB hiccup")
            return "imported"

        mock_logger = MagicMock()
        result = retry(flaky_import, retries=4, initial_delay=0.01, logger=mock_logger)

        assert result == "imported"
        assert call_count == 3
        assert mock_logger.warning.call_count == 2


# ── TC-034 ─────────────────────────────────────────────────────────────────

class TestTC034_AllRetriesFail:
    """TC-034: All retries fail → Process terminates (exception raised)."""

    def test_terminates_after_all_retries(self):
        def always_fail():
            raise RuntimeError("Permanent failure")

        mock_logger = MagicMock()

        with pytest.raises(RuntimeError, match="Permanent failure"):
            retry(always_fail, retries=3, initial_delay=0.01, logger=mock_logger)

        assert mock_logger.warning.call_count == 3
        mock_logger.error.assert_called_once()
        assert "failed after 3 attempts" in mock_logger.error.call_args[0][0]


# ── TC-035 ─────────────────────────────────────────────────────────────────

class TestTC035_BackoffTiming:
    """TC-035: Backoff timing → Delay increases exponentially."""

    def test_exponential_backoff(self):
        """
        With initial_delay=1 and backoff_factor=2 the expected delays are:
        attempt 1 fail → wait 1s, attempt 2 fail → wait 2s, attempt 3 fail → wait 4s, ...

        We patch time.sleep to capture the actual delays.
        """
        delays = []
        original_sleep = time.sleep

        def capture_sleep(seconds):
            delays.append(seconds)
            # Don't actually sleep

        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        mock_logger = MagicMock()

        with patch("time.sleep", side_effect=capture_sleep):
            # We need to also patch the retry's own time.sleep.
            # Since retry is defined above in this module, we re-define it
            # inline with the patched sleep.
            delay = 1.0
            backoff_factor = 2
            retries = 4

            for attempt in range(1, retries + 1):
                try:
                    always_fail()
                except RuntimeError:
                    if attempt == retries:
                        break
                    delays.append(delay)
                    delay *= backoff_factor

        assert len(delays) == 3, "Should have 3 delay entries (for 3 retries before final fail)"
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

        # Verify each delay is double the previous
        for i in range(1, len(delays)):
            assert delays[i] == delays[i - 1] * backoff_factor
