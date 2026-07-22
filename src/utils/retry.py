import time

from src.logger import logger
from src.config import RETRY_COUNT, RETRY_INITIAL_DELAY, RETRY_BACKOFF_FACTOR


def retry(
    func,
    *args,
    retries=RETRY_COUNT,
    initial_delay=RETRY_INITIAL_DELAY,
    backoff_factor=RETRY_BACKOFF_FACTOR,
    exceptions=(Exception,),
    **kwargs,
):
    """
    Retry a function using exponential backoff.

    Args:
        func: Function to execute.
        *args: Positional arguments for the function.
        retries: Maximum number of attempts.
        initial_delay: Delay before first retry (seconds).
        backoff_factor: Multiplier for exponential backoff.
        exceptions: Tuple of exceptions to retry.
        **kwargs: Keyword arguments for the function.
    """

    delay = initial_delay

    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)

        except exceptions as e:

            logger.warning(
                f"{func.__name__} failed "
                f"(Attempt {attempt}/{retries}) : {e}"
            )

            if attempt == retries:
                logger.error(
                    f"{func.__name__} failed after {retries} attempts."
                )
                raise

            logger.info(f"Retrying in {delay} seconds...")

            time.sleep(delay)

            delay *= backoff_factor