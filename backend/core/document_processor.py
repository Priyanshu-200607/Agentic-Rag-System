"""
Multi-modal document processor supporting PDF (with page-by-page streaming OCR fallback),
DOCX, CSV, JSON, TXT, MD, and standalone image formats (PNG, JPG, TIFF).
"""

import os
import json
import csv
from typing import List, Dict, Any
from core.chunking import create_parent_child_chunks

def process_file(path: str) -> str:
    """Extracts text from txt, md, pdf, docx, json, csv, and image files."""
    if not os.path.exists(path):
        return ""
        
    ext = os.path.splitext(path)[1].lower()
    
    if ext in [".txt", ".md"]:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
            
    elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        try:
            import pytesseract
            try:
                import cv2
                import numpy as np
                img = cv2.imread(path)
                if img is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                    return pytesseract.image_to_string(processed)
            except Exception:
                pass

            # Fallback to PIL Image
            from PIL import Image
            with Image.open(path) as pil_img:
                return pytesseract.image_to_string(pil_img)
        except Exception as e:
            print(f"[OCR] Error processing image {path}: {e}")
        return ""
        
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
        except Exception as e:
            print(f"[PDF] Error opening PDF {path}: {e}")
            return ""

        page_texts = []
        has_ocr_tools = False
        try:
            import cv2
            import numpy as np
            import pytesseract
            from pdf2image import convert_from_path
            has_ocr_tools = True
        except ImportError:
            pass

        for page_idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            # If page text is very sparse (< 40 chars) and OCR is available, fallback on that specific page
            if len(text) < 40 and has_ocr_tools:
                try:
                    # Convert single page to avoid loading entire multi-page PDF into memory
                    imgs = convert_from_path(path, first_page=page_idx + 1, last_page=page_idx + 1)
                    if imgs:
                        img_np = np.array(imgs[0])
                        gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
                        processed_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                        ocr_result = pytesseract.image_to_string(processed_img).strip()
                        if ocr_result:
                            text = ocr_result
                except Exception as e:
                    print(f"[OCR] Page {page_idx + 1} OCR fallback failed: {e}")
            if text:
                page_texts.append(text)

        return "\n\n".join(page_texts)
        
    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(path)
            return "\n".join(para.text for para in doc.paragraphs)
        except Exception as e:
            print(f"[DOCX] Error parsing {path}: {e}")
            return ""
            
    elif ext == ".json":
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        except Exception as e:
            print(f"[JSON] Error reading {path}: {e}")
            return ""
            
    elif ext == ".csv":
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                return "\n".join(", ".join(row) for row in reader)
        except Exception as e:
            print(f"[CSV] Error reading {path}: {e}")
            return ""
            
    return ""

def determine_document_access_level(file_path: str, explicit_confidentiality: str = None) -> tuple:
    """
    Returns (confidentiality, min_role) for Document-Level ABAC.
    Categories:
      - 'restricted'   -> min_role 'admin'   (master credentials, executive compensation)
      - 'confidential' -> min_role 'manager' (salaries, performance reviews, termination, nda)
      - 'internal'     -> min_role 'employee' (general departmental procedures, guidelines)
    """
    if explicit_confidentiality in ("restricted", "confidential", "internal", "public"):
        conf = explicit_confidentiality
        min_role = "admin" if conf == "restricted" else ("manager" if conf == "confidential" else "employee")
        return conf, min_role

    fname = os.path.basename(file_path).lower()
    restricted_keywords = ["master_key", "secret", "private_key", "admin_credential", "executive_comp"]
    confidential_keywords = ["salary", "salaries", "payroll", "compensation", "performance_review", "disciplinary", "termination", "audit_report", "tax_return", "nda"]
    
    if any(k in fname for k in restricted_keywords):
        return "restricted", "admin"
    elif any(k in fname for k in confidential_keywords):
        return "confidential", "manager"
    else:
        return "internal", "employee"
