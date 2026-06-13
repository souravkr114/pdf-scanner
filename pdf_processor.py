import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path, convert_from_bytes

def configure_ocr_paths(tesseract_cmd=None, poppler_path=None):
    """
    Configures environment paths for Tesseract OCR and Poppler binaries if specified.
    """
    if tesseract_cmd:
        # Resolve path to make sure it's valid
        tesseract_cmd = os.path.abspath(tesseract_cmd)
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    # If poppler_path is provided, we return it so convert_from_* can use it
    if poppler_path:
        return os.path.abspath(poppler_path)
    return None

def extract_text_direct(pdf_file_path_or_bytes):
    """
    Extracts text page-by-page using PyMuPDF.
    Works for digitally created PDFs.
    """
    pages_text = []
    
    if isinstance(pdf_file_path_or_bytes, bytes):
        doc = fitz.open(stream=pdf_file_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(pdf_file_path_or_bytes)
        
    for i, page in enumerate(doc):
        text = page.get_text()
        pages_text.append({
            "page_num": i + 1,
            "text": text.strip(),
            "method": "direct",
            "character_count": len(text.strip())
        })
        
    doc.close()
    return pages_text

def extract_text_ocr(pdf_file_path_or_bytes, tesseract_cmd=None, poppler_path=None):
    """
    Extracts text page-by-page converting pages to images first and then using Tesseract OCR.
    Works for scanned PDFs, handwritten notes, or images.
    """
    poppler_dir = configure_ocr_paths(tesseract_cmd, poppler_path)
    pages_text = []
    
    # Convert PDF to list of PIL Images
    if isinstance(pdf_file_path_or_bytes, bytes):
        images = convert_from_bytes(pdf_file_path_or_bytes, poppler_path=poppler_dir)
    else:
        images = convert_from_path(pdf_file_path_or_bytes, poppler_path=poppler_dir)
        
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        pages_text.append({
            "page_num": i + 1,
            "text": text.strip(),
            "method": "ocr",
            "character_count": len(text.strip())
        })
        
    return pages_text

def process_pdf(pdf_file_path_or_bytes, force_ocr=False, tesseract_cmd=None, poppler_path=None):
    """
    Main entry point to extract text from a PDF.
    By default, tries PyMuPDF first. If the resulting text is empty or very short,
    or if force_ocr=True, it falls back to Tesseract OCR.
    """
    # 1. Try direct extraction
    direct_pages = extract_text_direct(pdf_file_path_or_bytes)
    
    # Check if we got meaningful text (sum of character counts)
    total_char_count = sum(p["character_count"] for p in direct_pages)
    
    if force_ocr or total_char_count < 100:
        # If direct extraction found little to no text, fallback to OCR
        try:
            ocr_pages = extract_text_ocr(pdf_file_path_or_bytes, tesseract_cmd, poppler_path)
            return ocr_pages, True  # Return pages and OCR flag
        except Exception as e:
            # If OCR fails (e.g. paths not configured), return direct pages and error details
            if force_ocr:
                raise e
            return direct_pages, False
            
    return direct_pages, False
