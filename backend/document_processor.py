import os
import json
import csv
from pypdf import PdfReader
from docx import Document

def process_file(path: str) -> str:
    """Extracts text from txt, md, pdf, docx, json, and csv files."""
    ext = os.path.splitext(path)[1].lower()
    if ext in [".txt", ".md"]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        doc = Document(path)
        return "\n".join(para.text for para in doc.paragraphs)
    elif ext == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    elif ext == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return "\n".join(", ".join(row) for row in reader)
    return ""
