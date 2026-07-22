import time

from src.logger import logger


def retry(
    func,
    *args,
    retries=4,
    initial_delay=2,
    backoff_factor=2,
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