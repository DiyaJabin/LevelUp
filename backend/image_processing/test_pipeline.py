import os
import sys

# Maintain system environment path routing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ocr_service import QuizTextExtractorService

def run_system_tests():
    engine = QuizTextExtractorService()
    
    # Define your test paths inside sample_notes folder
    test_image = "sample_notes/sample_notes2.png"
    test_pdf = "sample_notes/sample_text.pdf" 
    
    print("\n" + "="*50)
    print("💎 RUNNING SYSTEM VALIDATION TESTING SUITE")
    print("="*50)

    # 1. Validate your working Image OCR
    if os.path.exists(test_image):
        print("\n⚙️ Testing Image Track Extraction...")
        img_result = engine.extract_content(test_image)
        print("\n✨ EXTRACTED IMAGE TEXT BLOCK: ✨")
        print("-" * 45)
        print(img_result)
        print("-" * 45)
    else:
        print(f"⚠️ Skip Image: Put your file at '{test_image}' to check image track extraction.")

    # 2. Validate your new PDF parser
    if os.path.exists(test_pdf):
        print("\n⚙️ Testing PDF Reader Extraction...")
        pdf_result = engine.extract_content(test_pdf)
        print("\n✨ EXTRACTED PDF TEXT BLOCK (First 1000 Chars): ✨")
        print("-" * 45)
        print(pdf_result[:1000]) 
        print("-" * 45)
    else:
        print(f"⚠️ Skip PDF: Place a test document at '{test_pdf}' to verify PDF parsing.")

if __name__ == "__main__":
    run_system_tests()