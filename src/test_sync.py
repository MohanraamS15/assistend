from src.db.sync_service import sync_database
from src.db.reports import generate_report


def main():
    sync_result = sync_database()

    report_path = generate_report(sync_result)

    print(sync_result)
    print(f"\nReport generated: {report_path}")


if __name__ == "__main__":
    main()