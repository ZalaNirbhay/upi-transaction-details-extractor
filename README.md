# UPI Payment Information Extractor

A professional tool to automatically extract transaction details from UPI payment screenshots (Google Pay, PhonePe, Paytm, etc.).

## 🚀 How to Run This Project

### Option 1: The Easy Way (One-Click)
1.  **Unzip** the folder.
2.  Double-click **`launcher.bat`**.
    - This will automatically install the required libraries and start the app.

### Option 2: Manual Run (Terminal)
1.  Open Terminal in the folder.
2.  Run: `pip install -r requirements.txt`
3.  Run: `python main.py`


### Option 2: If you are using Git
1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    ```
2.  **Navigate to the folder**:
    ```bash
    cd <folder-name>
    ```
3.  **Install Requirements**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the App**:
    ```bash
    python main.py
    ```

---

## 🛠️ Prerequisites
- **Python**: You need Python installed on your computer.
- **Tesseract OCR**: This app uses Tesseract to read text from images.
    - **Download**: [https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
    - **Install**: Run the installer. The app will automatically find it.

## 📖 How to Use
1.  **Select Input**: Click "Select Images" or "Select Folder" to choose your screenshots.
2.  **Select Output**: Choose where you want to save the Excel file.
3.  **Start**: Click "START EXTRACTION".
4.  **Done**: The Excel file will open automatically when finished.

## ❓ Troubleshooting
- **"Tesseract Not Found"**: Install Tesseract from the link above.
- **"No Text Found"**: Ensure your images are clear and not blurry.
