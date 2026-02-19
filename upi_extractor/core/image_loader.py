"""
Image Loader Module
-------------------
Handles loading images from files and folders.
Provides PIL-based loading and folder scanning utilities.
"""

import os
from PIL import Image

# Supported image file extensions
SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp')


def load_image_pil(image_path):
    """
    Load an image using PIL.

    Args:
        image_path (str): Path to the image file.

    Returns:
        PIL.Image.Image or None: Loaded image, or None on failure.
    """
    try:
        return Image.open(image_path)
    except Exception as e:
        print(f"[ImageLoader] Error loading {image_path}: {e}")
        return None


def load_images_from_folder(folder_path):
    """
    Recursively scan a folder and return paths to all supported image files.

    Args:
        folder_path (str): Path to the folder to scan.

    Returns:
        list[str]: List of absolute paths to image files found.
    """
    image_files = []

    for root, _, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                image_files.append(os.path.join(root, filename))

    return image_files
