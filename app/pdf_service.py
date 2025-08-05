import PyPDF2
import pytesseract
from pdf2image import convert_from_bytes
import io
from typing import Dict, Tuple, Optional, List
from .financial_extractor import FinancialDataExtractor

def extract_text_from_pdf(file_content: bytes, document_type: str) -> Tuple[str, int, Dict, Optional[Dict]]:
    """
    Extract text and financial data from PDF using both native text extraction and OCR
    """
    # Create a PDF file object
    pdf_file = io.BytesIO(file_content)
    
    # Create a PDF reader object
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    # Get number of pages
    num_pages = len(pdf_reader.pages)
    
    # Extract metadata
    metadata = pdf_reader.metadata if pdf_reader.metadata else {}
    
    full_text = []
    
    # Convert PDF to images and perform OCR
    images = convert_from_bytes(file_content)
    
    for i, image in enumerate(images):
        # First try native text extraction
        page = pdf_reader.pages[i]
        text = page.extract_text()
        
        # If no text is found, use OCR
        if not text.strip():
            text = pytesseract.image_to_string(image)
        
        full_text.append(text)
    
    # Initialize financial extractor
    financial_extractor = FinancialDataExtractor()
    
    # Extract financial data from the combined text
    full_text_str = "\n".join(full_text)
    financial_data = financial_extractor.extract_financial_data(full_text_str)
    
    return full_text_str, num_pages, metadata, financial_data