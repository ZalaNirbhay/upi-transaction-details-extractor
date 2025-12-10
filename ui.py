import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import os
import webbrowser
from extract import PaymentExtractor
from datetime import datetime

class PaymentApp(ttk.Window):
    def __init__(self):
        # 'flatly' is a very clean, modern flat theme
        super().__init__(themename="flatly")
        self.title("UPI Payment Information Extractor")
        self.geometry("800x650")
        self.place_window_center()
        
        self.extractor = PaymentExtractor()
        self.selected_files = []
        
        self.create_widgets()
        
    def place_window_center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def create_widgets(self):
        # Main Container with padding
        main_frame = ttk.Frame(self, padding=30)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # --- Header ---
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 25))
        
        # Icon/Logo placeholder (Unicode)
        logo_lbl = ttk.Label(header_frame, text="💳", font=("Segoe UI Emoji", 40))
        logo_lbl.pack(side=LEFT, padx=(0, 15))
        
        title_box = ttk.Frame(header_frame)
        title_box.pack(side=LEFT)
        
        title_lbl = ttk.Label(
            title_box, 
            text="UPI Payment Information Extractor", 
            font=("Segoe UI", 24, "bold"), 
            bootstyle="primary"
        )
        title_lbl.pack(anchor=W)
        
        subtitle_lbl = ttk.Label(
            title_box, 
            text="Automated OCR & Data Extraction Tool", 
            font=("Segoe UI", 10), 
            bootstyle="secondary"
        )
        subtitle_lbl.pack(anchor=W)

        # --- Content Grid ---
        
        # 1. Input Section (Card Style) - Unified Color (Primary)
        input_frame = ttk.Labelframe(main_frame, text=" 1. Input Source ", padding=20, bootstyle="primary")
        input_frame.pack(fill=X, pady=10)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=X, pady=(0, 10))
        
        select_files_btn = ttk.Button(
            btn_frame, 
            text="📂 Select Images", 
            command=self.select_images, 
            bootstyle="primary",
            width=20
        )
        select_files_btn.pack(side=LEFT, padx=(0, 10))
        
        select_folder_btn = ttk.Button(
            btn_frame, 
            text="📁 Select Folder", 
            command=self.select_folder, 
            bootstyle="outline-primary",
            width=20
        )
        select_folder_btn.pack(side=LEFT)
        
        self.files_lbl = ttk.Label(input_frame, text="No files selected", font=("Segoe UI", 9, "italic"), bootstyle="secondary")
        self.files_lbl.pack(anchor=W)

        # 2. Output Section (Card Style) - Unified Color (Primary)
        output_frame = ttk.Labelframe(main_frame, text=" 2. Output Destination ", padding=20, bootstyle="primary")
        output_frame.pack(fill=X, pady=10)
        
        out_inner_frame = ttk.Frame(output_frame)
        out_inner_frame.pack(fill=X)
        
        self.output_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "payment_details.xlsx"))
        
        path_entry = ttk.Entry(out_inner_frame, textvariable=self.output_path_var, state="readonly")
        path_entry.pack(side=LEFT, padx=(0, 10), expand=YES, fill=X)
        
        browse_btn = ttk.Button(
            out_inner_frame, 
            text="💾 Browse...", 
            command=self.browse_output, 
            bootstyle="outline-primary"
        )
        browse_btn.pack(side=LEFT)

        # 3. Action & Progress
        action_frame = ttk.Frame(main_frame, padding=10)
        action_frame.pack(fill=X, pady=10)
        
        self.start_btn = ttk.Button(
            action_frame, 
            text="🚀 START EXTRACTION", 
            command=self.start_extraction, 
            bootstyle="primary", # Monochromatic look
            width=30,
            state=DISABLED
        )
        self.start_btn.pack(pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100, 
            bootstyle="primary-striped" # Monochromatic look
        )
        self.progress_bar.pack(fill=X, pady=(10, 5))
        
        # 4. Activity Log
        log_frame = ttk.Labelframe(main_frame, text=" Activity Log ", padding=10, bootstyle="secondary")
        log_frame.pack(fill=BOTH, expand=YES, pady=(10, 0))
        
        self.log_area = ScrolledText(log_frame, height=6, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill=BOTH, expand=YES)
        
        # Footer / Watermark
        footer_lbl = ttk.Label(
            main_frame, 
            text="Developed by Zala Nirbhay", 
            font=("Segoe UI", 10, "italic", "bold"), 
            bootstyle="primary",
            cursor="hand2"
        )
        footer_lbl.pack(side=BOTTOM, pady=(10, 0), anchor=E)
        
        # Link to LinkedIn - Replace with actual URL if different
        footer_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://www.linkedin.com/in/zala-nirbhay-528a532b0"))
        
        self.log_message("Welcome! Please select images to begin.")

    def log_message(self, message):
        self.log_area.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(END, f"[{timestamp}] {message}\n")
        self.log_area.see(END)
        self.log_area.config(state='disabled')

    def select_images(self):
        files = filedialog.askopenfilenames(
            title="Select Payment Screenshots",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")]
        )
        if files:
            self.selected_files = list(files)
            self.update_file_label()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select Folder containing Images")
        if folder:
            files = []
            for root, _, filenames in os.walk(folder):
                for filename in filenames:
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        files.append(os.path.join(root, filename))
            self.selected_files = files
            self.update_file_label()

    def update_file_label(self):
        count = len(self.selected_files)
        if count > 0:
            self.files_lbl.config(text=f"✅ {count} images ready for processing", bootstyle="success")
            self.start_btn.config(state=NORMAL)
            self.log_message(f"Selected {count} images.")
        else:
            self.files_lbl.config(text="No files selected", bootstyle="secondary")
            self.start_btn.config(state=DISABLED)

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="payment_details.xlsx",
            title="Save Output Excel As"
        )
        if file_path:
            self.output_path_var.set(file_path)
            self.log_message(f"Output set to: {os.path.basename(file_path)}")

    def start_extraction(self):
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select images first.")
            return
        
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showwarning("Invalid Path", "Please select a valid output path.")
            return
            
        # Disable button
        self.start_btn.config(state=DISABLED)
        self.progress_var.set(0)
        self.log_message("Starting extraction process...")
        
        # Run in thread
        thread = threading.Thread(target=self.run_extraction_thread, args=(output_path,))
        thread.start()

    def run_extraction_thread(self, output_name):
        try:
            success, message = self.extractor.process_images(
                self.selected_files, 
                output_name, 
                self.update_progress
            )
            
            self.after(0, lambda: self.extraction_complete(success, message))
        except Exception as e:
            self.after(0, lambda: self.extraction_complete(False, str(e)))

    def update_progress(self, current, total, message):
        progress = (current / total) * 100
        self.after(0, lambda: self.progress_var.set(progress))
        # We don't want to log every single file to the text area as it might be too fast/cluttered, 
        # but we can log milestones or just rely on the progress bar.
        # Let's log every 5th file or if total is small.
        if total <= 5 or current % 5 == 0 or current == total:
             self.after(0, lambda: self.log_message(f"Processed {current}/{total}: {message}"))

    def extraction_complete(self, success, message):
        self.start_btn.config(state=NORMAL)
        self.log_message(f"COMPLETED: {message}")
        if success:
            messagebox.showinfo("Success", message)
            output_path = self.output_path_var.get()
            if os.path.exists(output_path):
                 try:
                     os.startfile(os.path.dirname(output_path))
                 except:
                     pass
        else:
            messagebox.showerror("Error", message)
