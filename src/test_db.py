from src.db.importer import import_csv

CSV_PATH = "output/header.csv"

if __name__ == "__main__":
    print("Starting CSV import...")

    import_csv(CSV_PATH, batch_size=50)

    print("CSV imported successfully!")