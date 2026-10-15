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
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        
        # Fallback to OCR if standard text extraction yields very little text
        if len(extracted_text.strip()) < 50:
            try:
                import cv2
                import numpy as np
                import pytesseract
                from pdf2image import convert_from_path
                
                print(f"[OCR] Initiating Tesseract OCR for scanned PDF: {path}")
                images = convert_from_path(path)
                ocr_text = ""
                for img in images:
                    # Pre-process image (grayscale, thresholding) for accuracy
                    img_np = np.array(img)
                    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                    processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                    ocr_text += pytesseract.image_to_string(processed_img) + "\n"
                return ocr_text
            except ImportError:
                print("[OCR] Dependencies missing (cv2, numpy, pytesseract, pdf2image). Returning original text.")
            except Exception as e:
                print(f"[OCR] Failed to run OCR on {path}: {e}")
                
        return extracted_text
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
