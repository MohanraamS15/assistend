import csv
import time

from sqlalchemy import text

from src.db.database import get_session
from src.db.models import SenderIDMappingStaging
from src.logger import logger


def import_csv(csv_path: str, batch_size: int = 5000):
    """
    Import Sender ID mappings from a CSV file into the staging table.
    """

    start_time = time.perf_counter()
    total_rows = 0
    batch = []

    logger.info("Starting staging import...")

    with get_session() as session:
        try:
            # Clear staging table before importing new data
            logger.info("Clearing staging table...")

            session.exec(
                text(
                    "TRUNCATE TABLE sender_id_mapping_staging RESTART IDENTITY"
                )
            )
            session.commit()

            logger.info("Staging table cleared.")

            with open(csv_path, mode="r", encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row in reader:

                    mapping = SenderIDMappingStaging(
                        sender_id=row["Header"].strip(),
                        sender_entity=row["Entity Name"].strip()
                    )

                    batch.append(mapping)

                    if len(batch) >= batch_size:
                        session.add_all(batch)
                        session.commit()

                        total_rows += len(batch)

                        logger.info(f"Imported {total_rows} rows into staging")

                        batch.clear()

                # Insert remaining rows
                if batch:
                    session.add_all(batch)
                    session.commit()

                    total_rows += len(batch)

                    logger.info(f"Imported {total_rows} rows into staging")

            elapsed = time.perf_counter() - start_time

            logger.info("=" * 50)
            logger.info("Staging Import Completed")
            logger.info(f"Total Rows Imported : {total_rows}")
            logger.info(f"Time Taken          : {elapsed:.2f} seconds")
            logger.info("=" * 50)

        except Exception:
            session.rollback()
            logger.exception("Staging import failed.")
            raise