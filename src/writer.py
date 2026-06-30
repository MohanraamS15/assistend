import csv
from pathlib import Path
from config import CSV_PATH



def write_records(records):
    """
    Append parsed records to the CSV.
    """

    if not records:
        return

    file_exists = CSV_PATH.exists()

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "S.No",
                "Header",
                "Entity Name",
                "Purpose"
            ],
            extrasaction="ignore"
        )

        if not file_exists:
            writer.writeheader()

        writer.writerows(records)