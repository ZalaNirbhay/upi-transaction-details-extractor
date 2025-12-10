import pytesseract
import sys
import os

def check_tesseract():
    print("Checking Tesseract Installation...")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract found! Version: {version}")
        return True
    except pytesseract.TesseractNotFoundError:
        print("❌ Tesseract not found in PATH.")
        print("Please install Tesseract-OCR and add it to your System PATH.")
        print("Download: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        print(f"❌ Error checking Tesseract: {e}")
        return False

if __name__ == "__main__":
    if check_tesseract():
        print("\nReady to run the app!")
    else:
        print("\nPlease fix the issues above before running the app.")
    input("\nPress Enter to exit...")
