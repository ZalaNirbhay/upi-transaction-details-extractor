import os
import sys

def find_tesseract():
    common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"D:\Program Files\Tesseract-OCR\tesseract.exe",
        os.path.join(os.getenv('LOCALAPPDATA'), r"Tesseract-OCR\tesseract.exe")
    ]
    
    print("Searching for Tesseract...")
    for path in common_paths:
        if os.path.exists(path):
            print(f"Found Tesseract at: {path}")
            return path
            
    # Check PATH
    try:
        import shutil
        path = shutil.which("tesseract")
        if path:
            print(f"Found Tesseract in PATH at: {path}")
            return path
    except:
        pass
        
    print("Tesseract NOT found.")
    return None

if __name__ == "__main__":
    path = find_tesseract()
    if path:
        with open("tesseract_path.txt", "w") as f:
            f.write(path)
    else:
        with open("tesseract_path.txt", "w") as f:
            f.write("NOT_FOUND")
