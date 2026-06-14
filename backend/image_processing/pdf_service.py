import os
from pypdf import PdfReader

class PDFTextExtractorService:
    def __init__(self):
        print("⚡ PDF Extraction Engine Loaded!")

    def extract_text_from_pdf(self, pdf_path):
        """
        Reads a digital PDF document and extracts all text content 
        page by page into a clean string for quiz generation.
        """
        if not os.path.exists(pdf_path):
            return f"Error: PDF file not found at {pdf_path}"

        try:
            reader = PdfReader(pdf_path)
            full_text = []

            print(f"📄 Reading {len(reader.pages)} pages from the PDF...")
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text.strip():
                    full_text.append(page_text.strip())

            return "\n\n".join(full_text)

        except Exception as e:
            return f"PDF Extraction Error: {str(e)}"