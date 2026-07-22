import csv
from datetime import datetime
from pathlib import Path

from src.logger import logger

REPORT_DIR = Path("output/sync_reports")


def generate_report(sync_result):
    """
    Generate a CSV report for synchronization changes.
    """

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    report_path = REPORT_DIR / f"sync_report_{timestamp}.csv"

    with open(report_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([
            "Operation",
            "Sender ID",
            "Old Entity",
            "New Entity"
        ])

        # INSERTS
        for sender_id, sender_entity in sync_result["insert_rows"]:
            writer.writerow([
                "INSERT",
                sender_id,
                "",
                sender_entity
            ])

        # UPDATES
        for sender_id, old_entity, new_entity in sync_result["update_rows"]:
            writer.writerow([
                "UPDATE",
                sender_id,
                old_entity,
                new_entity
            ])

        # DELETES
        for sender_id, sender_entity in sync_result["delete_rows"]:
            writer.writerow([
                "DELETE",
                sender_id,
                sender_entity,
                ""
            ])

    logger.info(f"Sync report generated: {report_path}")

    return report_path