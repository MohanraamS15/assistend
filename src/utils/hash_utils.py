import hashlib
import json
from datetime import datetime

from src.config import METADATA_FILE


def calculate_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def read_previous_hash():
    if not METADATA_FILE.exists():
        return None

    with open(METADATA_FILE, "r") as file:
        metadata = json.load(file)

    return metadata.get("last_hash")


def save_current_hash(hash_value):
    metadata = {
        "last_hash": hash_value,
        "last_sync": datetime.now().isoformat()
    }

    with open(METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=4)