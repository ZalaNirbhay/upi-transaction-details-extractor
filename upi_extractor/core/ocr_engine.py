"""
OCR Engine Module
-----------------
Handles Tesseract OCR configuration and text extraction from images.
Automatically detects Tesseract installation on Windows.
"""

import os
import pytesseract
from datetime import datetime
from upi_extractor.utils.image_preprocessing import preprocess_image
from upi_extractor.core.image_loader import load_image_pil


class OCREngine:
    """
    Wrapper around Tesseract OCR.
    Auto-detects Tesseract path and provides text extraction.
    """

    def __init__(self):
        self._configure_tesseract()

    def _configure_tesseract(self):
        """
        Attempt to find Tesseract executable in common Windows paths.
        If already accessible via PATH, no action is needed.
        """
        # Check if Tesseract is already accessible
        try:
            pytesseract.get_tesseract_version()
            return
        except Exception:
            pass

        # Search common installation paths
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]

        # Add user-local path if LOCALAPPDATA is set
        local_app = os.getenv('LOCALAPPDATA')
        if local_app:
            common_paths.append(
                os.path.join(local_app, r"Tesseract-OCR\tesseract.exe")
            )

        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return

    def _get_ocr_config(self, source_type):
        """
        Return Tesseract config string based on extraction source type.

        Args:
            source_type (str): 'screenshot', 'passbook', 'camera', or 'auto'.

        Returns:
            str: Tesseract custom config flags.
        """
        configs = {
            # Screenshots: structured block of text
            'screenshot': '--psm 6',
            # Passbook/statements: uniform text layout
            'passbook': '--psm 6',
            # Camera photos: auto page segmentation (handles rotation/angles)
            'camera': '--psm 3',
            # Auto: let Tesseract decide
            'auto': '',
        }
        return configs.get(source_type, '')

    def extract_text(self, image_path, source_type="auto"):
        """
        Extract raw text from an image using Tesseract OCR.

        First attempts with preprocessed image (grayscale + binarized).
        Falls back to raw PIL image if preprocessing fails.

        Args:
            image_path (str): Path to the image file.
            source_type (str): Source type for OCR config tuning.

        Returns:
            str: Extracted text, or empty string on failure.
        """
        try:
            config = self._get_ocr_config(source_type)

            # Try with preprocessed image first (better OCR accuracy)
            processed_img = preprocess_image(image_path)
            if processed_img is not None:
                text = pytesseract.image_to_string(processed_img, config=config)
            else:
                # Fallback to raw PIL image
                img = load_image_pil(image_path)
                text = pytesseract.image_to_string(img, config=config)
            return text

        except Exception as e:
            # Log error silently — will be improved in Step 10
            log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'ocr_errors.log')
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now()}: Error on {image_path}: {e}\n")
            return ""
