# UPI Payment Extractor 💳

> **Developed by Zala Nirbhay**

A professional desktop application to extract payment details from **UPI Screenshots** and **Bank Passbook Photos** using OCR. Automatically parses text and exports structured data to Excel.

## 🚀 Features

- **Multi-Source Support**: Handles UPI payment screenshots and Bank Passbook photos.
- **Batch Processing**: Select individual images or entire folders.
- **Smart Parsing**: Automatically extracts key fields (Amount, Date, Sender, Receiver, Account No, IFSC, etc.).
- **Excel Export**:
  - Professional formatting (colors, bold headers).
  - Financial summaries (Total Credit/Debit).
  - **Append Mode**: Add new data to an existing Excel file without overwriting.
- **Review & Edit**: Interactive table to verify and edit data before exporting.
- **Dark/Light Mode**: Toggle effectively between themes.

## 🛠️ Prerequisites

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
2.  **Tesseract OCR**:
    - Download and install Tesseract: [Windows Installer (UB-Mannheim)](https://github.com/UB-Mannheim/tesseract/wiki)
    - **IMPORTANT**: The app automatically looks for Tesseract in `C:\Program Files\Tesseract-OCR\tesseract.exe` or `C:\Program Files (x86)\Tesseract-OCR\tesseract.exe`.
    - If installed elsewhere, add it to your System PATH or update the code.

## 📦 Installation

1.  **Clone or Download** the repository.
2.  **Run the Installer/Launcher** (Windows):
    - Double-click `launcher.bat`.
    - This script will automatically:
        - Check for Python.
        - Install required dependencies (`customtkinter`, `pandas`, `pytesseract`, etc.).
        - Launch the application.

## 🖥️ Usage

1.  **Launch** the app via `launcher.bat`.
2.  **Select Source**: Choose "Screenshot" or "Passbook" (or leave as "Auto").
3.  **Load Images**: Click **Select Files** or **Select Folder**.
4.  **Extract**: Click **START EXTRACTION**.
5.  **Review**:
    - Extracted data appears in the table.
    - Click any row to see the image preview.
    - Edit any cell if OCR made a mistake.
6.  **Export**:
    - Click **EXPORT**.
    - Check **Append** if you want to add to an existing Excel sheet.
    - Choose a file name and save.

## 📂 Project Structure

- `main.py`: Entry point.
- `launcher.bat`: One-click installer & runner.
- `upi_extractor/`: Core source code.
    - `core/`: OCR logic and regex parsing.
    - `ui/`: CustomTkinter GUI.
    - `export/`: Excel generation logic.
- `requirements.txt`: Python dependencies.

## 👨‍💻 Developer

**Zala Nirbhay**
[LinkedIn Profile](https://www.linkedin.com/in/zala-nirbhay-528a532b0)
