from PIL import Image, ImageDraw, ImageFont
import pytesseract
from extract import PaymentExtractor
import os

def create_dummy_image(path):
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        header_font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        font = ImageFont.load_default()
        header_font = ImageFont.load_default()

    d.text((250, 50), "Payment Successful", fill='black', font=header_font)
    d.text((50, 150), "Paid to: John Doe", fill='black', font=font)
    d.text((50, 200), "UPI ID: john.doe@oksbi", fill='black', font=font)
    d.text((50, 250), "Amount: ₹ 1,500.00", fill='black', font=font)
    d.text((50, 300), "Txn ID: 123456789012", fill='black', font=font)
    d.text((50, 350), "Date: 12 Jan 2023", fill='black', font=font)
    d.text((50, 400), "Time: 10:30 AM", fill='black', font=font)
    
    img.save(path)
    print(f"Created dummy image at {path}")

def test_pipeline():
    print("--- Starting Pipeline Test ---")
    
    # 1. Check Tesseract
    try:
        ver = pytesseract.get_tesseract_version()
        print(f"Tesseract Version: {ver}")
    except Exception as e:
        print(f"CRITICAL ERROR: Tesseract not found or not working. {e}")
        print("Please ensure Tesseract is installed and in your PATH.")
        return

    # 2. Create Image
    img_path = "test_payment.png"
    create_dummy_image(img_path)
    
    # 3. Run Extraction
    extractor = PaymentExtractor()
    
    print("\n--- Extracting Text ---")
    raw_text = extractor.extract_text(img_path)
    print(f"Raw Text Length: {len(raw_text)}")
    print(f"Raw Text Preview:\n{raw_text.strip()}\n")
    
    if not raw_text.strip():
        print("ERROR: No text extracted. Tesseract might be failing on the image.")
        return

    print("\n--- Parsing Details ---")
    details = extractor.parse_details(raw_text, "test_payment.png")
    
    print("Extracted Details:")
    for key, value in details.items():
        print(f"{key}: {value}")
        
    # Validation
    if details['Amount'] == '1500.00' and details['Payment Status'] == 'SUCCESS':
        print("\n✅ TEST PASSED: Core extraction logic is working.")
    else:
        print("\n❌ TEST FAILED: Extraction logic missed some fields.")

if __name__ == "__main__":
    test_pipeline()
