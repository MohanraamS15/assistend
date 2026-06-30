from pathlib import Path
import fitz
from config import PDF_PATH


def get_document():
    """
    Open the PDF once and return the document object.
    """
    return fitz.open(PDF_PATH)