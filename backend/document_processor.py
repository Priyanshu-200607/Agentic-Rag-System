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

            # Robust fallback to PIL Image
            from PIL import Image
            with Image.open(path) as pil_img:
                return pytesseract.image_to_string(pil_img)
        except Exception as e:
            print(f"[OCR] Error processing image {path}: {e}")
        return ""
    elif ext == ".pdf":
        try:
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

def create_parent_child_chunks(
    text: str,
    source_file: str = "",
    department: str = "",
    parent_size: int = 1200,
    parent_overlap: int = 200,
    child_size: int = 300,
    child_overlap: int = 50
) -> list:
    """
    Creates hierarchical Parent-Child chunks.
    Small child chunks (~300 chars) are stored for high-precision vector search.
    Each child chunk references its surrounding parent section (~1200 chars) for coherent LLM context.
    """
    if not text or not text.strip():
        return []
        
    import uuid
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=parent_size, chunk_overlap=parent_overlap)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=child_size, chunk_overlap=child_overlap)
    
    parent_docs = parent_splitter.split_text(text)
    hierarchical_chunks = []
    
    for p_idx, parent_text in enumerate(parent_docs):
        parent_id = f"{os.path.basename(source_file)}_{p_idx}_{uuid.uuid4().hex[:6]}"
        child_docs = child_splitter.split_text(parent_text)
        
        for c_idx, child_text in enumerate(child_docs):
            child_clean = child_text.strip()
            if not child_clean:
                continue
            hierarchical_chunks.append({
                "id": f"{parent_id}_c{c_idx}",
                "text": child_clean,
                "parent_id": parent_id,
                "parent_text": parent_text.strip(),
                "source": source_file,
                "department": department
            })
            
    return hierarchical_chunks

