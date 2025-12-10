import cv2
import numpy as np
from PIL import Image

def preprocess_image(image_path):
    """
    Reads an image and applies preprocessing to improve OCR accuracy.
    """
    try:
        # Read image using cv2
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to binarize the image
        # This helps in separating text from background
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
        
        return denoised
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def load_image_pil(image_path):
    """
    Loads an image using PIL (for display or fallback).
    """
    try:
        return Image.open(image_path)
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None
