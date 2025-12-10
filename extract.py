import pytesseract
import re
import os
import pandas as pd
from datetime import datetime
from utils import preprocess_image, load_image_pil
from PIL import Image

# Set Tesseract path if needed (User might need to configure this)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class PaymentExtractor:
    def __init__(self):
        # Auto-detect Tesseract
        self.configure_tesseract()
        
        # Compiled regex for better performance and cleaner code
        self.patterns = {
            'amount': [
                r'[₹Rs]\.?\s*([\d,]+\.?\d{0,2})',
                r'Amount\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Paid\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Total\s*Payable\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'^\s*[₹Rs]\.?\s*([\d,]+\.?\d{0,2})\s*$' # Standalone amount line
            ],
            'upi_id': [
                r'([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)',
                r'UPI\s*ID\s*[:\-]?\s*([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)',
                r'VPA\s*[:\-]?\s*([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)'
            ],
            'txn_id': [
                r'Txn\s*ID\s*[:\-]?\s*(\w+)',
                r'Transaction\s*ID\s*[:\-]?\s*(\w+)',
                r'UPI\s*Ref\s*No\s*[:\-]?\s*(\d+)',
                r'Ref\s*No\s*[:\-]?\s*(\d+)',
                r'UTR\s*[:\-]?\s*(\d+)',
                r'Google\s*Transaction\s*ID\s*[:\-]?\s*([\w\-]+)',
                r'Debited\s*from\s*[:\-]?\s*(\w+)' # Sometimes appears here
            ],
            'date': [
                r'(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})'
            ],
            'time': [
                r'(\d{1,2}:\d{2}\s*[APap][Mm])',
                r'(\d{1,2}:\d{2})'
            ],
            'status': [
                r'(SUCCESS|FAILED|PENDING|PROCESSING|COMPLETED)',
                r'Payment\s*(Successful|Failed|Pending|Processing|Completed)',
                r'Transaction\s*(Successful|Failed|Pending)'
            ]
        }

    def configure_tesseract(self):
        """
        Attempts to find Tesseract executable in common paths.
        """
        try:
            pytesseract.get_tesseract_version()
            return
        except:
            pass
            
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.join(os.getenv('LOCALAPPDATA'), r"Tesseract-OCR\tesseract.exe")
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return

    def extract_text(self, image_path):
        """
        Extracts raw text from an image using Tesseract OCR.
        """
        try:
            processed_img = preprocess_image(image_path)
            if processed_img is not None:
                # psm 6 is good for blocks of text, psm 4 or 3 might be better for full receipts
                # We'll stick to default or try 6.
                text = pytesseract.image_to_string(processed_img)
            else:
                img = load_image_pil(image_path)
                text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            # Silent fail with log is better for production
            with open("ocr_errors.log", "a") as f:
                f.write(f"{datetime.now()}: Error on {image_path}: {e}\n")
            return ""

    def parse_details(self, text, filename):
        """
        Parses extracted text to find specific payment details.
        """
        details = {
            'File Name': filename,
            'UPI Transaction ID': '',
            'Google Transaction ID': '',
            'Reference ID': '',
            'From (Sender)': '',
            'To (Receiver)': '',
            'UPI ID / VPA': '',
            'Bank Name': '',
            'Amount': '',
            'Payment Status': '',
            'Date': '',
            'Time': '',
            'Transaction Note': '',
            'All Extracted Text': text.strip()
        }

        def find_match(pattern_key, target_text):
            for pattern in self.patterns[pattern_key]:
                match = re.search(pattern, target_text, re.IGNORECASE)
                if match:
                    return match.group(1) if match.groups() else match.group(0)
            return ''

        # Amount Cleaning
        raw_amount = find_match('amount', text)
        if raw_amount:
            # Remove commas, spaces, and ensure it looks like a number
            clean_amount = re.sub(r'[^\d\.]', '', raw_amount)
            try:
                # Verify if it's a valid float
                float(clean_amount)
                details['Amount'] = clean_amount
            except ValueError:
                details['Amount'] = raw_amount # Keep raw if check fails
        
        details['UPI ID / VPA'] = find_match('upi_id', text)
        details['Date'] = find_match('date', text)
        details['Time'] = find_match('time', text)
        
        # Status parsing
        status_raw = find_match('status', text).upper()
        if 'SUCCESS' in status_raw or 'COMPLETED' in status_raw:
            details['Payment Status'] = 'SUCCESS'
        elif 'FAIL' in status_raw:
            details['Payment Status'] = 'FAILED'
        elif 'PENDING' in status_raw or 'PROCESSING' in status_raw:
            details['Payment Status'] = 'PENDING'

        # Transaction IDs - Logic to differentiate
        # Find all potential IDs
        all_ids = []
        for pattern in self.patterns['txn_id']:
            all_ids.extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Deduplicate and assign
        for txn in set(all_ids):
            txn = txn.strip()
            if not txn: continue
            
            if 'CIC' in txn or (len(txn) > 20 and not txn.isdigit()):
                details['Google Transaction ID'] = txn
            elif txn.isdigit() and len(txn) >= 12:
                details['Reference ID'] = txn
            else:
                # If it looks like a mix of letters and numbers, likely a Bank Ref or UPI Txn ID
                if len(txn) > 8:
                     details['UPI Transaction ID'] = txn

        # Heuristics for Sender/Receiver/Bank
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            # Bank Name often contains "Bank"
            if 'Bank' in line and not details['Bank Name']:
                # Avoid "Bank Reference No" etc.
                if len(line) < 40 and not any(x in line.lower() for x in ['ref', 'id', 'no']):
                    details['Bank Name'] = line

            # Receiver often follows "To" or is at the top
            if (line.lower().startswith('to') or line.lower() == 'paid to') and not details['To (Receiver)']:
                clean_line = re.sub(r'^to\s*[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                if clean_line:
                    details['To (Receiver)'] = clean_line
                elif i + 1 < len(lines):
                    details['To (Receiver)'] = lines[i+1]
            
            # Sender
            if line.lower().startswith('from') and not details['From (Sender)']:
                clean_line = re.sub(r'^from\s*[:\-]?\s*', '', line, flags=re.IGNORECASE).strip()
                if clean_line:
                    details['From (Sender)'] = clean_line
                elif i + 1 < len(lines):
                    details['From (Sender)'] = lines[i+1]

        return details

    def process_images(self, image_paths, output_excel_path, progress_callback=None):
        """
        Processes a list of images and saves results to Excel.
        """
        all_data = []
        total = len(image_paths)
        
        for i, img_path in enumerate(image_paths):
            if progress_callback:
                progress_callback(i + 1, total, f"Processing {os.path.basename(img_path)}...")
            
            raw_text = self.extract_text(img_path)
            parsed_data = self.parse_details(raw_text, os.path.basename(img_path))
            all_data.append(parsed_data)
        
        df = pd.DataFrame(all_data)
        
        # Ensure output path ends with .xlsx
        if not output_excel_path.lower().endswith('.xlsx'):
            output_excel_path += '.xlsx'
            
        try:
            df.to_excel(output_excel_path, index=False)
            return True, f"Successfully saved to {output_excel_path}"
        except Exception as e:
            return False, f"Error saving Excel: {e}"
