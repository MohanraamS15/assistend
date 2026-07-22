import requests

from src.config import PDF_URL, PDF_PATH


def download_pdf():

    response = requests.get(PDF_URL)

    print("Status Code:", response.status_code)
    print("Content-Type:", response.headers.get("Content-Type"))

    response.raise_for_status()

    with open(PDF_PATH, "wb") as file:
        file.write(response.content)

