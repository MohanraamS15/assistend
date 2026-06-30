import requests

from config import PDF_URL, PDF_PATH


def download_pdf():

    response = requests.get(PDF_URL)

    response.raise_for_status()

    with open(PDF_PATH, "wb") as file:
        file.write(response.content)