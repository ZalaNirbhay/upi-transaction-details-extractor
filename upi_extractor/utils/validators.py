"""
Validators Module
-----------------
Placeholder for future validation functions (Step 4+).
Will include image quality checks, data validation, etc.
"""


def validate_image_path(path):
    """Check if a path points to a valid image file."""
    import os
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp')
    return os.path.isfile(path) and path.lower().endswith(valid_extensions)
