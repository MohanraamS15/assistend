import csv
import time

from src.db.database import get_session
from src.db.models import SenderIDMapping
from src.logger import logger


def import_csv(csv_path: str, batch_size: int = 5000):
    """
    Import Sender ID mappings from a CSV file into PostgreSQL.
    """

    start_time = time.time()
    total_rows = 0
    batch = []

    logger.info("Starting CSV import...")

    with get_session() as session:
        try:
            with open(csv_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:

                    mapping = SenderIDMapping(
                        sender_id=row["Header"],
                        sender_entity=row["Entity Name"]
                    )

                    batch.append(mapping)

                    if len(batch) >= batch_size:
                        session.add_all(batch)
                        session.commit()

                        total_rows += len(batch)

                        logger.info(f"Imported {total_rows} rows")

                        batch.clear()

                # Insert remaining rows
                if batch:
                    session.add_all(batch)
                    session.commit()

                    total_rows += len(batch)

                    logger.info(f"Imported {total_rows} rows")

            elapsed = time.time() - start_time

            logger.info("=" * 50)
            logger.info("CSV Import Completed")
            logger.info(f"Total Rows Imported : {total_rows}")
            logger.info(f"Time Taken          : {elapsed:.2f} seconds")
            logger.info("=" * 50)

        except Exception as e:
            session.rollback()
            logger.exception("Import failed.")
            raise e