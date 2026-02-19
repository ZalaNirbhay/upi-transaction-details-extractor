"""
UPI Payment Extractor — Entry Point
Run this file to launch the application.
"""

from upi_extractor.ui.main_ui import PaymentApp

if __name__ == "__main__":
    app = PaymentApp()
    app.mainloop()
