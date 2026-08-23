"""
Module for extracting text from various resume formats (PDF, DOCX, TXT)
"""
import os
from pathlib import Path

def extract_text_from_resume(file_path: str) -> str:
    """
    Extract text from resume file (PDF, DOCX, or TXT)
    
    Args:
        file_path: Path to the resume file
        
    Returns:
        Extracted text from the resume
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")
    
    try:
        if file_extension == '.pdf':
            return extract_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return extract_from_docx(file_path)
        elif file_extension == '.txt':
            return extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    except Exception as e:
        raise Exception(f"Error extracting text from {file_path}: {str(e)}")

def extract_from_pdf(file_path: Path) -> str:
    """Extract text from PDF file"""
    text = ""
    
    # Try pdfplumber first (better text extraction)
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        text = text.strip()
        if text and len(text) > 0:
            return text
    except ImportError:
        pass  # Fall back to PyPDF2
    except Exception:
        pass  # Fall back to PyPDF2
    
    # Fall back to PyPDF2
    try:
        import PyPDF2
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            if num_pages == 0:
                raise ValueError("PDF file appears to be empty or corrupted")
            
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        text = text.strip()
        
        if not text or len(text) == 0:
            raise ValueError(
                "Could not extract text from PDF. The PDF might be:\n"
                "- Image-based (scanned) - requires OCR software\n"
                "- Password protected\n"
                "- Corrupted\n"
                "- Empty\n\n"
                "Try installing pdfplumber for better extraction: pip install pdfplumber\n"
                "Or convert the PDF to DOCX/TXT format"
            )
        
        return text
    except ImportError:
        raise ImportError(
            "PyPDF2 is required for PDF processing. Install it with: pip install PyPDF2\n"
            "For better results, also install: pip install pdfplumber"
        )
    except ValueError as e:
        raise ValueError(str(e))
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")

def extract_from_docx(file_path: Path) -> str:
    """Extract text from DOCX file"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except ImportError:
        raise ImportError("python-docx is required for DOCX processing. Install it with: pip install python-docx")
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")

def extract_from_txt(file_path: Path) -> str:
    """Extract text from TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        raise Exception(f"Error reading TXT file: {str(e)}")

