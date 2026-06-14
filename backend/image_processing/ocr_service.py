
import cv2
import torch
import os
import numpy as np
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from .image_preprocessing import load_and_clean_image
from .pdf_service import PDFTextExtractorService

class QuizTextExtractorService:
    def __init__(self):
        print("🔄 Loading Native Text Extraction Engine...")
        # Load your successfully downloaded TrOCR local weights
        self.processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        self.model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
        # Load your fast digital PDF assistant
        self.pdf_reader = PDFTextExtractorService()

    def extract_content(self, file_path):
        """
        Main website routing endpoint. Automatically detects file extension 
        and sends it to the correct extraction helper function.
        """
        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"

        _, file_extension = os.path.splitext(file_path.lower())

        # 🎯 Branch 1: If the user uploads a digital PDF document
        if file_extension == '.pdf':
            print("Detected file type: PDF")
            return self.pdf_reader.extract_text_from_pdf(file_path)

        # 🎯 Branch 2: If the user uploads an image file (Using your exact golden code logic)
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            print("Detected file type: IMAGE")
            return self.extract_clean_text(file_path)

        else:
            return f"Error: Unsupported file format '{file_extension}'"

    def extract_clean_text(self, image_path):
        """
        YOUR GOLDEN CODE - UNCHANGED
        Segments paragraph text into lines using native OpenCV contours,
        then transcribes lines sequentially for quiz processing.
        """
        try:
            print("🧼 Filtering image noise and binarizing...")
            thresh = load_and_clean_image(image_path)
            
            # Invert the image so text is white and background is black for contour mapping
            inverted = cv2.bitwise_not(thresh)
            
            # Dilate horizontally to connect loose cursive words into solid text lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 5))
            dilated = cv2.dilate(inverted, kernel, iterations=1)
            
            # Find the boundaries of each text line block
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort contours from top to bottom so the text reads in order
            bounding_boxes = [cv2.boundingRect(c) for c in contours]
            bounding_boxes = sorted(bounding_boxes, key=lambda b: b[1])
            
            # Re-read raw image for clean crop arrays
            raw_img = cv2.imread(image_path)
            rgb_img = cv2.cvtColor(raw_img, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_img)
            
            lines_extracted = []
            print(f"🧠 Transcribing {len(bounding_boxes)} detected handwriting blocks...")
            
            for x, y, w, h in bounding_boxes:
                # Filter out tiny specks, dots, or small paper noise marks
                if h < 15 or w < 30:
                    continue
                    
                # Crop the specific sentence line
                line_crop = pil_image.crop([x, y, x + w, y + h])
                
                # Process via your local TrOCR transformer engine
                pixel_values = self.processor(images=line_crop, return_tensors="pt").pixel_values
                with torch.no_grad():
                    generated_ids = self.model.generate(pixel_values)
                
                line_text = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                if line_text.strip():
                    lines_extracted.append(line_text.strip())
            
            return "\n".join(lines_extracted)

        except Exception as e:
            return f"Extraction Error: {str(e)}"