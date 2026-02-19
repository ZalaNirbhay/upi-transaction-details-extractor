"""
Image Preprocessing Module
--------------------------
Provides functions to preprocess images before OCR extraction.
Includes grayscale conversion, thresholding, and denoising.
"""

import cv2


def preprocess_image(image_path):
    """
    Reads an image and applies preprocessing to improve OCR accuracy.

    Steps:
        1. Load image with OpenCV
        2. Convert to grayscale
        3. Apply Otsu's binarization (separates text from background)
        4. Denoise the result

    Args:
        image_path (str): Absolute path to the image file.

    Returns:
        numpy.ndarray or None: Preprocessed image array, or None on failure.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply Otsu's thresholding to binarize
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Denoise the binarized image
        denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)

        return denoised

    except Exception as e:
        print(f"[Preprocessing] Error processing {image_path}: {e}")
        return None
