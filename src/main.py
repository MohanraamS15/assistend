import time

from src.extractor import get_document
from src.parser import parse_page
from src.writer import write_records
from src.logger import logger
from src.config import CSV_PATH
from src.db.importer import import_csv
from src.db.sync_service import sync_database
from src.db.reports import generate_report


def main():
    start_time = time.perf_counter()

    logger.info("Starting Header Sync Job...")

    # Remove old CSV if it exists
    if CSV_PATH.exists():
        CSV_PATH.unlink()

    total_records = 0

    doc = get_document()

    try:
        total_pages = len(doc)

        for page_number in range(total_pages):

            try:
                page = doc[page_number]

                lines = page.get_text().splitlines()

                records = parse_page(lines)

                write_records(records)

                total_records += len(records)

                if (page_number + 1) % 100 == 0:
                    logger.info(
                        f"Processed {page_number + 1}/{total_pages} pages"
                    )

            except Exception:
                logger.exception(
                    f"Failed processing page {page_number + 1}"
                )

    finally:
        doc.close()

    end_time = time.perf_counter()

    logger.info(
        f"""
==========================
PDF Processed Successfully

Pages Processed : {total_pages}
Records Written : {total_records}
CSV Generated   : {CSV_PATH}

Time Taken       : {end_time - start_time:.2f} seconds

==========================
"""
    )

    # Import CSV into PostgreSQL
    logger.info("Starting PostgreSQL import...")

    # Import CSV into staging table
    logger.info("Starting staging import...")

    import_csv(CSV_PATH)

    logger.info("Staging import completed.")

    # Synchronize staging with main table
    sync_stats = sync_database()
    report_path = generate_report(sync_stats)

    logger.info("=" * 60)
    logger.info("Synchronization Summary")
    logger.info(f"Inserted        : {sync_stats['inserted']}")
    logger.info(f"Updated         : {sync_stats['updated']}")
    logger.info(f"Deleted         : {sync_stats['deleted']}")
    logger.info(f"Sync Time       : {sync_stats['sync_time']:.2f} seconds")
    logger.info(f"Report          : {report_path}")
    logger.info("=" * 60)

    logger.info("Header Sync Job Completed.")


if __name__ == "__main__":
    main()