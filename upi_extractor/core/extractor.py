"""
Payment Data Extractor Module
------------------------------
Parses raw OCR text to extract structured UPI payment details.
Supports multiple source types with specialized extraction:
  - screenshot / camera / auto: UPI payment screenshots
  - passbook: Bank passbook / statement images (full banking details)
"""

import re
import os
from upi_extractor.core.ocr_engine import OCREngine
from upi_extractor.export.excel_exporter import export_to_excel


class PaymentExtractor:
    """
    Main extraction engine.
    Coordinates OCR → parsing → export pipeline.
    """

    def __init__(self):
        self.ocr = OCREngine()

        # ── UPI Screenshot Patterns ──────────────────────────────────
        self.patterns = {
            'amount': [
                r'[₹Rs]\.?\s*([\d,]+\.?\d{0,2})',
                r'Amount\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Paid\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Total\s*Payable\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'^\s*[₹Rs]\.?\s*([\d,]+\.?\d{0,2})\s*$',
            ],
            'upi_id': [
                r'([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)',
                r'UPI\s*ID\s*[:\-]?\s*([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)',
                r'VPA\s*[:\-]?\s*([a-zA-Z0-9\.\-_]+@[a-zA-Z]+)',
            ],
            'txn_id': [
                r'Txn\s*ID\s*[:\-]?\s*(\w+)',
                r'Transaction\s*ID\s*[:\-]?\s*(\w+)',
                r'UPI\s*Ref\s*No\s*[:\-]?\s*(\d+)',
                r'Ref\s*No\s*[:\-]?\s*(\d+)',
                r'UTR\s*[:\-]?\s*(\d+)',
                r'Google\s*Transaction\s*ID\s*[:\-]?\s*([\w\-]+)',
                r'Debited\s*from\s*[:\-]?\s*(\w+)',
            ],
            'date': [
                r'(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
            ],
            'time': [
                r'(\d{1,2}:\d{2}\s*[APap][Mm])',
                r'(\d{1,2}:\d{2})',
            ],
            'status': [
                r'(SUCCESS|FAILED|PENDING|PROCESSING|COMPLETED)',
                r'Payment\s*(Successful|Failed|Pending|Processing|Completed)',
                r'Transaction\s*(Successful|Failed|Pending)',
            ],
        }

        # ── Passbook / Bank Statement – First Page Patterns ────────
        # These patterns handle SAME-LINE  "label: value"  pairs.
        # Multi-line gaps are handled by _scan_passbook_lines().
        # ALL text-capturing groups use GREEDY .+ to grab full content.

        self.passbook_patterns = {

            # ── Identity ─────────────────────────────────────────
            'account_holder': [
                # "Account Holder Name : Nirbhay Zala" — LONGER alt first!
                r'(?:Account|A/?c)\s*Holder\s*Name\s*[:\-]?\s*(.+)',
                # "Account Holder : Nirbhay Zala"
                r'(?:Account|A/?c)\s*Holder\s*[:\-]\s*(.+)',
                # "Name of Account Holder : Nirbhay Zala"
                r'Name\s*of\s*(?:Account\s*)?Holder\s*[:\-]?\s*(.+)',
                # "Holder Name : Nirbhay Zala"
                r'Holder\s*Name\s*[:\-]?\s*(.+)',
                # "Customer Name : Nirbhay Zala"
                r'Customer\s*(?:Name)?\s*[:\-]\s*(.+)',
                # "Name : Nirbhay Zala" — only matches if "Name" is first word on line
                r'(?:^|\n)\s*Name\s*[:\-]\s*(.+)',
                # "Mr. Nirbhay Zala" / "Shri Nirbhay Zala" — space only, not \s
                r'(?:Mr|Mrs|Ms|Shri|Smt|Sri)\.?\s+([A-Za-z][A-Za-z .]{2,})',
            ],

            'account_number': [
                # "A/c No. : 1234 5678 9012" or "Account Number: 123456789012"
                r'(?:A/?c|Account|Acct)\s*(?:No\.?|Number|Num|#)\s*[:\-.]?\s*(\d[\d\s\-]{6,}\d)',
                # "Savings A/c 123456789012"
                r'(?:Savings|Current)\s*(?:A/?c|Account)\s*[:\-]?\s*(\d[\d\s\-]{6,}\d)',
                # "A/C: 123456789012"
                r'A/?[Cc]\s*[:\-.]?\s*(\d{9,18})',
            ],

            'account_type': [
                r'\b(Savings|Current|Fixed\s*Deposit|Recurring\s*Deposit)\b\s*(?:Account|A/?c|Bank)?',
                r'\b(SB|CA|FD|RD)\b\s*(?:Account|A/?c)',
            ],

            # ── Bank / Branch ────────────────────────────────────
            'bank_name': [
                r'(?:^|\n|\s)((?:State\s*Bank\s*of\s*India|SBI|HDFC\s*Bank|ICICI\s*Bank|'
                r'Axis\s*Bank|Kotak\s*(?:Mahindra)?|PNB|BOB|Bank\s*of\s*Baroda|'
                r'Union\s*Bank(?:\s*of\s*India)?|Canara\s*Bank|Indian\s*Bank|BOI|Bank\s*of\s*India|'
                r'Central\s*Bank|IDBI\s*Bank|Yes\s*Bank|IndusInd\s*Bank|Federal\s*Bank|'
                r'South\s*Indian\s*Bank|Bandhan\s*Bank|RBL\s*Bank|UCO\s*Bank|'
                r'Punjab\s*National\s*Bank|Indian\s*Overseas\s*Bank|'
                r'Allahabad\s*Bank|Dena\s*Bank|Syndicate\s*Bank|Oriental\s*Bank|'
                r'Corporation\s*Bank|Andhra\s*Bank|Vijaya\s*Bank|'
                r'Karnataka\s*Bank|Karur\s*Vysya|City\s*Union\s*Bank|'
                r'Tamilnad\s*Mercantile|Dhanlaxmi\s*Bank|Lakshmi\s*Vilas|'
                r'Nainital\s*Bank|Jammu\s*&?\s*Kashmir\s*Bank|'
                r'Bank\s*of\s*Maharashtra|IDFC\s*First)'
                r'(?:\s*(?:Bank|Ltd|Limited))?)(?=[\s,.\n]|$)',
            ],

            'branch_name': [
                # "Branch : Main Branch Ahmedabad"
                r'Branch\s*(?:Name)?\s*[:\-]\s*(.+)',
                r'Branch\s*(?:Name)?\s*[:\-]?\s*(.{3,})',
            ],

            'ifsc_code': [
                r'IFSC\s*(?:Code)?\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})',
                r'(?:^|[\s:])([A-Z]{4}0[A-Z0-9]{6})(?:\s|$)',
            ],

            'micr_code': [
                r'MICR\s*(?:Code|No\.?)?\s*[:\-]?\s*(\d{9})\b',
            ],

            # ── First-page specific fields ───────────────────────
            'cif_number': [
                r'(?:CIF|CIF\s*(?:No\.?|Number|ID))\s*[:\-]?\s*(\d{6,})',
                r'Customer\s*(?:ID|Id)\s*[:\-]?\s*(\d{6,})',
            ],

            'nomination': [
                r'Nominat(?:ion|ee)\s*[:\-]?\s*(.+)',
            ],

            'joint_holder': [
                r'(?:Joint\s*(?:Holder|Account\s*Holder|Name))\s*[:\-]?\s*(.+)',
            ],

            'address': [
                r'(?:Address|Addr\.?)\s*[:\-]\s*(.+)',
            ],

            'mobile_number': [
                r'(?:Mobile|Phone|Contact|Mob\.?)\s*(?:No\.?|Number)?\s*[:\-]?\s*(\+?\d[\d\s\-]{8,}\d)',
            ],

            'date_of_opening': [
                r'(?:Date\s*of\s*(?:Opening|Open)|Opened?\s*(?:on|Date)|DOO)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(?:Date\s*of\s*(?:Opening|Open)|Opened?\s*(?:on|Date)|DOO)\s*[:\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
            ],

            # ── Financial (only if visible on first page) ────────
            'credit_amount': [
                r'(?:Credit|Credited)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.\d{1,2})',
                r'(?:Credit|Credited)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+)',
                r'(?:Deposit)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'[₹Rs]\.?\s*([\d,]+\.?\d{0,2})\s*(?:Cr|Credit)',
            ],
            'debit_amount': [
                r'(?:Debit|Debited|Dr)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.\d{1,2})',
                r'(?:Debit|Debited|Dr)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+)',
                r'(?:Withdrawal|Withdraw)\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'[₹Rs]\.?\s*([\d,]+\.?\d{0,2})\s*(?:Dr|Debit)',
            ],
            'balance': [
                r'(?:Available|Avl\.?)\s*Bal(?:ance)?\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.\d{1,2})',
                r'(?:Available|Avl\.?)\s*Bal(?:ance)?\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+)',
                r'Balance\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.\d{1,2})',
                r'Balance\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+)',
            ],
            'opening_balance': [
                r'(?:Opening|Open(?:ing)?\.?)\s*Bal(?:ance)?\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Op\.?\s*Bal\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
            ],
            'closing_balance': [
                r'(?:Closing|Clos(?:ing)?\.?)\s*Bal(?:ance)?\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
                r'Cl\.?\s*Bal\.?\s*[:\-]?\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})',
            ],

            # ── Transaction fields (may appear if statement) ─────
            'cheque_number': [
                r'(?:Cheque|Chq|CHQ)\s*(?:No\.?|Number|#)?\s*[:\-]?\s*(\d{6,})',
            ],
            'narration': [
                r'(?:Narration|Description|Particulars|Remark|Details)\s*[:\-]?\s*(.+)',
            ],
            'transaction_type': [
                r'\b(NEFT|RTGS|IMPS|UPI|ATM|POS|ECS|NACH|CASH|CHQ|FT|TRANSFER)\b',
                r'(?:Mode|Type|Channel)\s*[:\-]?\s*(NEFT|RTGS|IMPS|UPI|ATM|POS|ECS|NACH)',
            ],
            'date': [
                r'(?:Date|Dt|Txn\s*Date|Value\s*Date)\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})',
                r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})',
            ],
            'reference_number': [
                r'(?:Ref|Reference)\s*(?:No\.?|Number|ID|#)?\s*[:\-]?\s*(\d{8,})',
                r'UTR\s*(?:No\.?)?\s*[:\-]?\s*(\d{8,})',
                r'(?:Txn|Transaction)\s*(?:No\.?|ID|#)\s*[:\-]?\s*(\w{8,})',
            ],
        }

        # ── Multi-line label → value mappings ────────────────────
        # When a label appears on one line and the value on the NEXT
        # non-empty line, these patterns catch them.
        # Format: (label_regex, field_key, value_regex)
        self._passbook_multiline_labels = [
            # Account Number: label alone → digits on next line
            (r'(?:A/?c|Account|Acct)\s*(?:No\.?|Number|Num|#)\s*[:\-.]?\s*$',
             'Account Number', r'^\s*(\d[\d\s\-]{6,}\d)\s*$'),
            # Account Holder / Customer Name / Name → text on next line
            (r'(?:Account|A/?c)\s*(?:Holder|Holder\s*Name)\s*[:\-]?\s*$',
             'Account Holder', r'^\s*(.{2,})\s*$'),
            (r'(?:Customer)\s*(?:Name)?\s*[:\-]?\s*$',
             'Account Holder', r'^\s*(.{2,})\s*$'),
            (r'(?:Holder)\s*(?:Name)?\s*[:\-]?\s*$',
             'Account Holder', r'^\s*(.{2,})\s*$'),
            (r'^\s*Name\s*[:\-]?\s*$',
             'Account Holder', r'^\s*([A-Za-z].*)\s*$'),
            # Branch
            (r'(?:Branch)\s*(?:Name)?\s*[:\-]?\s*$',
             'Branch Name', r'^\s*(.{3,})\s*$'),
            # IFSC / MICR
            (r'IFSC\s*(?:Code)?\s*[:\-]?\s*$',
             'IFSC Code', r'^\s*([A-Z]{4}0[A-Z0-9]{6})\s*$'),
            (r'MICR\s*(?:Code|No\.?)?\s*[:\-]?\s*$',
             'MICR Code', r'^\s*(\d{9})\s*$'),
            # Balance
            (r'(?:Balance|Bal\.?)\s*[:\-]?\s*$',
             'Balance (₹)', r'^\s*[₹Rs]?\.?\s*([\d,]+\.?\d{0,2})\s*$'),
            # Reference
            (r'(?:Ref|Reference)\s*(?:No\.?|Number|ID)?\s*[:\-]?\s*$',
             'Reference Number', r'^\s*(\d{8,})\s*$'),
            # CIF
            (r'(?:CIF|Customer\s*ID)\s*(?:No\.?|Number)?\s*[:\-]?\s*$',
             'CIF Number', r'^\s*(\d{6,})\s*$'),
            # Nomination
            (r'Nominat(?:ion|ee)\s*[:\-]?\s*$',
             'Nomination', r'^\s*(.{2,})\s*$'),
            # Address
            (r'(?:Address|Addr\.?)\s*[:\-]?\s*$',
             'Address', r'^\s*(.{3,})\s*$'),
            # Joint Holder
            (r'(?:Joint)\s*(?:Holder|Account\s*Holder|Name)\s*[:\-]?\s*$',
             'Joint Holder', r'^\s*(.{2,})\s*$'),
            # Mobile
            (r'(?:Mobile|Phone|Contact|Mob\.?)\s*(?:No\.?|Number)?\s*[:\-]?\s*$',
             'Mobile Number', r'^\s*(\+?\d[\d\s\-]{8,}\d)\s*$'),
            # Date of Opening
            (r'(?:Date\s*of\s*(?:Opening|Open)|Opened?\s*(?:on|Date)|DOO)\s*[:\-]?\s*$',
             'Date of Opening', r'^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*$'),
            # Narration / Particulars
            (r'(?:Narration|Particulars|Remark)\s*[:\-]?\s*$',
             'Narration', r'^\s*(.{3,})\s*$'),
            # Cheque
            (r'(?:Cheque|Chq)\s*(?:No\.?|Number)?\s*[:\-]?\s*$',
             'Cheque Number', r'^\s*(\d{6,})\s*$'),
        ]

    # ══════════════════════════════════════════════════════════════════
    #  COMMON HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _find_match(self, pattern_key, text, pattern_dict=None):
        """Search text for the first match in a pattern group."""
        patterns = (pattern_dict or self.patterns).get(pattern_key, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip() if match.groups() else match.group(0).strip()
        return ''

    def _clean_amount(self, raw):
        """Remove commas/spaces from an amount string, validate as number."""
        if not raw:
            return ''
        clean = re.sub(r'[^\d\.]', '', raw)
        try:
            float(clean)
            return clean
        except ValueError:
            return raw

    # ══════════════════════════════════════════════════════════════════
    #  PASSBOOK EXTRACTION
    # ══════════════════════════════════════════════════════════════════

    def _scan_passbook_lines(self, text, details):
        """
        Second-pass line scanner for passbook text.

        Handles the common OCR case where the field label is on one line
        and the value appears on the NEXT non-empty line. Also skips blank
        lines between label and value (common in passbook OCR output).

        Additionally picks up standalone account numbers and IFSC codes.

        Args:
            text (str): Raw OCR text.
            details (dict): Partially filled dict, modified in place.
        """
        lines = [line.strip() for line in text.split('\n')]
        num_lines = len(lines)

        def _get_next_nonempty(start_idx):
            """Find next non-empty line after start_idx, skipping blanks."""
            j = start_idx + 1
            while j < num_lines and not lines[j].strip():
                j += 1
            if j < num_lines:
                return lines[j].strip()
            return ''

        for i, line in enumerate(lines):
            if not line:
                continue

            next_line = _get_next_nonempty(i)

            # ── Check each multi-line label pattern ──
            for label_re, field_key, value_re in self._passbook_multiline_labels:
                if details.get(field_key):
                    continue

                if re.search(label_re, line, re.IGNORECASE):
                    if next_line:
                        val_match = re.match(value_re, next_line, re.IGNORECASE)
                        if val_match:
                            details[field_key] = val_match.group(1).strip()

            # ── Standalone account number (line of 9-18 digits only) ──
            if not details.get('Account Number'):
                acc_match = re.match(r'^\s*(\d{9,18})\s*$', line)
                if acc_match:
                    details['Account Number'] = acc_match.group(1)

            # ── Standalone IFSC ──
            if not details.get('IFSC Code'):
                ifsc_match = re.match(r'^\s*([A-Z]{4}0[A-Z0-9]{6})\s*$', line)
                if ifsc_match:
                    val = ifsc_match.group(1)
                    if val != details.get('MICR Code'):
                        details['IFSC Code'] = val

    def _parse_passbook_details(self, text, filename):
        """
        Extract all possible bank passbook first-page and statement fields.

        Uses a two-pass approach:
          Pass 1 — Regex patterns for inline label:value pairs (same line)
          Pass 2 — Line scanner for multi-line label → value gaps

        Args:
            text (str): Raw OCR text from passbook image.
            filename (str): Source image filename.

        Returns:
            dict: Extracted passbook fields.
        """
        pb = self.passbook_patterns

        # ── Pass 1: Regex extraction (inline label:value) ──
        details = {
            # ─ Identity ─
            'File Name': filename,
            'Bank Name': self._find_match('bank_name', text, pb),
            'Account Holder': self._find_match('account_holder', text, pb),
            'Account Number': self._find_match('account_number', text, pb),
            'Account Type': self._find_match('account_type', text, pb),
            # ─ Bank codes ─
            'IFSC Code': self._find_match('ifsc_code', text, pb),
            'MICR Code': self._find_match('micr_code', text, pb),
            'Branch Name': self._find_match('branch_name', text, pb),
            'CIF Number': self._find_match('cif_number', text, pb),
            # ─ First-page extras ─
            'Date of Opening': self._find_match('date_of_opening', text, pb),
            'Nomination': self._find_match('nomination', text, pb),
            'Joint Holder': self._find_match('joint_holder', text, pb),
            'Address': self._find_match('address', text, pb),
            'Mobile Number': self._find_match('mobile_number', text, pb),
            # ─ Transaction / Financial ─
            'Date': self._find_match('date', text, pb),
            'Transaction Type': self._find_match('transaction_type', text, pb),
            'Narration': self._find_match('narration', text, pb),
            'Reference Number': self._find_match('reference_number', text, pb),
            'Cheque Number': self._find_match('cheque_number', text, pb),
            'Credit (₹)': self._clean_amount(
                self._find_match('credit_amount', text, pb)
            ),
            'Debit (₹)': self._clean_amount(
                self._find_match('debit_amount', text, pb)
            ),
            'Balance (₹)': self._clean_amount(
                self._find_match('balance', text, pb)
            ),
            'Opening Balance (₹)': self._clean_amount(
                self._find_match('opening_balance', text, pb)
            ),
            'Closing Balance (₹)': self._clean_amount(
                self._find_match('closing_balance', text, pb)
            ),
            'All Extracted Text': text.strip(),
        }

        # ── Pass 2: Line scanner for multi-line gaps ──
        self._scan_passbook_lines(text, details)

        # ══════════════════════════════════════════════════════════
        # POST-PROCESSING — clean up and validate extracted data
        # ══════════════════════════════════════════════════════════

        # Clean account number — remove spaces/dashes
        if details['Account Number']:
            details['Account Number'] = re.sub(
                r'[\s\-]', '', details['Account Number']
            )

        # Normalize account type
        acc_type = details['Account Type'].upper() if details['Account Type'] else ''
        type_map = {
            'SB': 'Savings', 'SAVINGS': 'Savings',
            'CA': 'Current', 'CURRENT': 'Current',
            'FD': 'Fixed Deposit', 'FIXED DEPOSIT': 'Fixed Deposit',
            'RD': 'Recurring Deposit', 'RECURRING DEPOSIT': 'Recurring Deposit',
        }
        if acc_type in type_map:
            details['Account Type'] = type_map[acc_type]

        # Prevent cross-contamination: IFSC should not equal MICR
        if (details['IFSC Code'] and details['MICR Code']
                and details['IFSC Code'] == details['MICR Code']):
            details['MICR Code'] = ''

        # Prevent balance from matching MICR code
        bal = details.get('Balance (₹)', '')
        if bal and len(bal.replace('.', '').replace(',', '')) == 9:
            if bal == details.get('MICR Code', '').replace(' ', ''):
                details['Balance (₹)'] = ''

        # Clean mobile number — remove spaces/dashes
        if details.get('Mobile Number'):
            details['Mobile Number'] = re.sub(
                r'[\s\-]', '', details['Mobile Number']
            )

        return details

    # ══════════════════════════════════════════════════════════════════
    #  UPI SCREENSHOT EXTRACTION
    # ══════════════════════════════════════════════════════════════════

    def parse_details(self, text, filename, source_type="auto"):
        """
        Parse extracted OCR text into structured payment details.
        Routes to passbook-specific parser when source_type is 'passbook'.

        Args:
            text (str): Raw OCR text.
            filename (str): Source image filename.
            source_type (str): One of 'screenshot', 'passbook', 'camera', 'auto'.

        Returns:
            dict: Extracted payment fields.
        """
        # Passbook mode → dedicated parser with banking fields
        if source_type == 'passbook':
            return self._parse_passbook_details(text, filename)

        # Default UPI screenshot parsing
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
            'All Extracted Text': text.strip(),
        }

        # --- Amount ---
        details['Amount'] = self._clean_amount(
            self._find_match('amount', text)
        )

        # --- UPI ID, Date, Time ---
        details['UPI ID / VPA'] = self._find_match('upi_id', text)
        details['Date'] = self._find_match('date', text)
        details['Time'] = self._find_match('time', text)

        # --- Payment Status ---
        status_raw = self._find_match('status', text).upper()
        if 'SUCCESS' in status_raw or 'COMPLETED' in status_raw:
            details['Payment Status'] = 'SUCCESS'
        elif 'FAIL' in status_raw:
            details['Payment Status'] = 'FAILED'
        elif 'PENDING' in status_raw or 'PROCESSING' in status_raw:
            details['Payment Status'] = 'PENDING'

        # --- Transaction IDs (differentiate by format) ---
        all_ids = []
        for pattern in self.patterns['txn_id']:
            all_ids.extend(re.findall(pattern, text, re.IGNORECASE))

        for txn in set(all_ids):
            txn = txn.strip()
            if not txn:
                continue
            if 'CIC' in txn or (len(txn) > 20 and not txn.isdigit()):
                details['Google Transaction ID'] = txn
            elif txn.isdigit() and len(txn) >= 12:
                details['Reference ID'] = txn
            elif len(txn) > 8:
                details['UPI Transaction ID'] = txn

        # --- Sender / Receiver / Bank (heuristic line scan) ---
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            if 'Bank' in line and not details['Bank Name']:
                if len(line) < 40 and not any(
                    x in line.lower() for x in ['ref', 'id', 'no']
                ):
                    details['Bank Name'] = line

            if (
                line.lower().startswith('to') or line.lower() == 'paid to'
            ) and not details['To (Receiver)']:
                clean = re.sub(
                    r'^to\s*[:\-]?\s*', '', line, flags=re.IGNORECASE
                ).strip()
                if clean:
                    details['To (Receiver)'] = clean
                elif i + 1 < len(lines):
                    details['To (Receiver)'] = lines[i + 1]

            if line.lower().startswith('from') and not details['From (Sender)']:
                clean = re.sub(
                    r'^from\s*[:\-]?\s*', '', line, flags=re.IGNORECASE
                ).strip()
                if clean:
                    details['From (Sender)'] = clean
                elif i + 1 < len(lines):
                    details['From (Sender)'] = lines[i + 1]

        return details

    # ══════════════════════════════════════════════════════════════════
    #  PIPELINE
    # ══════════════════════════════════════════════════════════════════

    def process_images(self, image_paths, output_excel_path,
                       progress_callback=None, source_type="auto"):
        """
        Full extraction pipeline: OCR → parse → export.

        Args:
            image_paths (list[str]): Paths to images to process.
            output_excel_path (str): Destination Excel file path.
            progress_callback (callable): fn(current, total, message) for progress.
            source_type (str): Source type ('screenshot', 'passbook', 'camera', 'auto').

        Returns:
            tuple: (success: bool, message: str)
        """
        all_data, summary = self.extract_all(image_paths, progress_callback, source_type)
        return export_to_excel(all_data, output_excel_path)

    def extract_all(self, image_paths, progress_callback=None, source_type="auto"):
        """
        OCR + parse only — returns extracted data without exporting.

        Includes:
          - Error recovery: continues on failure, logs error for each image
          - Duplicate detection: skips images producing identical data
          - Processing summary: counts of success/fail/duplicate

        Args:
            image_paths (list[str]): Paths to images to process.
            progress_callback (callable): fn(current, total, message) for progress.
            source_type (str): Source type ('screenshot', 'passbook', 'camera', 'auto').

        Returns:
            tuple: (list[dict], dict) — extracted data and summary stats.
                   Summary keys: 'success', 'failed', 'duplicates', 'errors'
        """
        all_data = []
        total = len(image_paths)
        seen_hashes = set()

        summary = {
            'success': 0,
            'failed': 0,
            'duplicates': 0,
            'errors': [],  # list of (filename, error_message)
        }

        for i, img_path in enumerate(image_paths):
            filename = os.path.basename(img_path)

            if progress_callback:
                progress_callback(
                    i + 1, total, f"Processing {filename}..."
                )

            try:
                raw_text = self.ocr.extract_text(img_path, source_type=source_type)
                parsed_data = self.parse_details(
                    raw_text, filename, source_type=source_type
                )

                # ── Duplicate detection (hash key fields, not raw text) ──
                key_fields = {k: v for k, v in parsed_data.items()
                              if k not in ('File Name', 'All Extracted Text') and v}
                data_hash = hash(frozenset(key_fields.items()))

                if data_hash in seen_hashes:
                    summary['duplicates'] += 1
                    if progress_callback:
                        progress_callback(
                            i + 1, total, f"⏭️ Skipped duplicate: {filename}"
                        )
                    continue

                seen_hashes.add(data_hash)
                all_data.append(parsed_data)
                summary['success'] += 1

            except Exception as e:
                summary['failed'] += 1
                summary['errors'].append((filename, str(e)))
                # Create error record so user can see it in the table
                all_data.append({
                    'File Name': filename,
                    'Error': str(e),
                })
                if progress_callback:
                    progress_callback(
                        i + 1, total, f"❌ Error: {filename} — {e}"
                    )

        return all_data, summary


