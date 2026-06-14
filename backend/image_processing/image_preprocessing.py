import cv2
import numpy as np
import os

def load_and_clean_image(image_path):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"⚠️ Image not found: {image_path}")

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh