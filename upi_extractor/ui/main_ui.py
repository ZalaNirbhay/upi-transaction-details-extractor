"""
Main UI Module — Dark-Themed CustomTkinter Interface
-----------------------------------------------------
Modern, professional desktop GUI for the UPI Payment Extractor.

Workflow:
  1. Select images / folder
  2. Choose extraction source type
  3. Run extraction (OCR + parse)
  4. Review & edit results in interactive table
  5. Export to formatted Excel
"""

import customtkinter as ctk
import os
import threading
import webbrowser
from tkinter import filedialog, messagebox, END
from datetime import datetime
from PIL import Image

from upi_extractor.core.extractor import PaymentExtractor
from upi_extractor.core.image_loader import load_images_from_folder
from upi_extractor.export.excel_exporter import export_to_excel

# ─── Appearance Configuration ───────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Columns to display in the results table (key fields only)
UPI_DISPLAY_COLS = [
    'File Name', 'Amount', 'From (Sender)', 'To (Receiver)',
    'Payment Status', 'Date', 'UPI Transaction ID',
]
PASSBOOK_DISPLAY_COLS = [
    'File Name', 'Account Holder', 'Account Number', 'Bank Name',
    'IFSC Code', 'Branch Name', 'Credit (₹)', 'Debit (₹)', 'Balance (₹)',
]


class PaymentApp(ctk.CTk):
    """
    Main application window.
    Provides the full extraction workflow:
        select → extract → review/edit → export.
    """

    def __init__(self):
        super().__init__()

        # ── Window Setup ──
        self.title("UPI Payment Extractor")
        self.geometry("1100x820")
        self.minsize(900, 700)
        self._center_window()

        # ── State ──
        self.extractor = PaymentExtractor()
        self.selected_files = []
        self.source_type_var = ctk.StringVar(value="auto")
        self.extracted_data = []       # list[dict] from extraction
        self.result_entries = []       # list[dict of CTkEntry widgets]
        self.result_columns = []       # column names in view
        self.all_result_columns = []   # all columns from extraction
        self.processing_summary = {}   # success/fail/duplicate counts
        self.append_var = ctk.BooleanVar(value=False)
        self.theme_var = ctk.StringVar(value="dark")

        # ── Build UI ──
        self._create_widgets()

    # ══════════════════════════════════════════════════════════════════
    #  WINDOW HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        w = 1100
        h = 820
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # ══════════════════════════════════════════════════════════════════
    #  UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════

    def _create_widgets(self):
        """Build all UI components."""

        # ── Scrollable Main Container ──
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=25, pady=15)

        # ── 1. Header Section ──
        self._build_header(main_frame)

        # ── 2. Top controls (source, input, output in a compact row) ──
        controls = ctk.CTkFrame(main_frame, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 8))

        # Left: Input + Source
        left_col = ctk.CTkFrame(controls, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._build_input_section(left_col)
        self._build_source_type_section(left_col)

        # Right: Output + Action
        right_col = ctk.CTkFrame(controls, fg_color="transparent")
        right_col.pack(side="right", fill="x", expand=True, padx=(8, 0))

        self._build_output_section(right_col)
        self._build_action_bar(right_col)

        # ── 3. Progress Section ──
        self._build_progress_section(main_frame)

        # ── 4. Results Section (hidden until extraction completes) ──
        self._build_results_section(main_frame)

        # ── 5. Status / Log Section ──
        self._build_status_section(main_frame)

        # ── 6. Footer ──
        self._build_footer(main_frame)

    # ── Header ──────────────────────────────────────────────────────

    def _build_header(self, parent):
        """App title, subtitle, and theme toggle."""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        # ── Left: Icon + Title ──
        icon_label = ctk.CTkLabel(
            header,
            text="💳",
            font=ctk.CTkFont(family="Segoe UI Emoji", size=40),
        )
        icon_label.pack(side="left", padx=(0, 12))

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_block,
            text="UPI Payment Extractor",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#1a73e8", "#8ab4f8"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_block,
            text="Automated OCR & Data Extraction Tool",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray",
        ).pack(anchor="w")

        # ── Right: Theme toggle ──
        theme_frame = ctk.CTkFrame(header, fg_color="transparent")
        theme_frame.pack(side="right", padx=(10, 0))

        ctk.CTkLabel(
            theme_frame,
            text="☀️",
            font=ctk.CTkFont(size=16),
        ).pack(side="left", padx=(0, 4))

        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="",
            width=42,
            height=22,
            switch_width=38,
            switch_height=18,
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light",
            variable=self.theme_var,
        )
        self.theme_switch.pack(side="left", padx=2)

        ctk.CTkLabel(
            theme_frame,
            text="🌙",
            font=ctk.CTkFont(size=16),
        ).pack(side="left", padx=(4, 0))

        # Thin separator line below header
        sep = ctk.CTkFrame(parent, height=2, fg_color=("#d0d0d0", "#3a3a3a"))
        sep.pack(fill="x", pady=(0, 8))

    # ── Extraction Source Type ──────────────────────────────────────

    def _build_source_type_section(self, parent):
        """Radio buttons to choose extraction source type."""
        section = ctk.CTkFrame(parent, corner_radius=10)
        section.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            section,
            text="🔍  Extraction Source",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 6))

        radio_row = ctk.CTkFrame(section, fg_color="transparent")
        radio_row.pack(fill="x", padx=15, pady=(0, 10))

        sources = [
            ("📱 Screenshot", "screenshot"),
            ("🏦 Passbook", "passbook"),
            ("📷 Camera", "camera"),
            ("🔄 Auto", "auto"),
        ]

        for text, value in sources:
            ctk.CTkRadioButton(
                radio_row,
                text=text,
                variable=self.source_type_var,
                value=value,
                font=ctk.CTkFont(size=11),
                command=self._on_source_changed,
            ).pack(side="left", padx=(0, 12))

    def _on_source_changed(self):
        """Log when user changes extraction source."""
        source = self.source_type_var.get()
        labels = {
            "screenshot": "Transaction Screenshot",
            "passbook": "Passbook / Statement",
            "camera": "Camera Photo",
            "auto": "All Sources (Auto)",
        }
        self._log(f"Source type: {labels.get(source, source)}")

    # ── Input Source ────────────────────────────────────────────────

    def _build_input_section(self, parent):
        """Image / folder selection."""
        section = ctk.CTkFrame(parent, corner_radius=10)
        section.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            section,
            text="📥  Input Source",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 6))

        btn_row = ctk.CTkFrame(section, fg_color="transparent")
        btn_row.pack(fill="x", padx=15)

        ctk.CTkButton(
            btn_row,
            text="📂 Select Images",
            command=self._select_images,
            width=140,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="📁 Select Folder",
            command=self._select_folder,
            width=140,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
        ).pack(side="left")

        self.files_label = ctk.CTkLabel(
            section,
            text="No files selected",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray",
        )
        self.files_label.pack(anchor="w", padx=15, pady=(6, 10))

    # ── Output Destination ─────────────────────────────────────────

    def _build_output_section(self, parent):
        """Output Excel path picker."""
        section = ctk.CTkFrame(parent, corner_radius=10)
        section.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            section,
            text="📤  Output Destination",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 6))

        path_row = ctk.CTkFrame(section, fg_color="transparent")
        path_row.pack(fill="x", padx=15, pady=(0, 10))

        default_output = os.path.join(os.getcwd(), "payment_details.xlsx")
        self.output_path_var = ctk.StringVar(value=default_output)

        self.output_entry = ctk.CTkEntry(
            path_row,
            textvariable=self.output_path_var,
            state="readonly",
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
        )
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            path_row,
            text="💾 Browse...",
            command=self._browse_output,
            width=110,
            height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
        ).pack(side="left")

    # ── Action Bar ─────────────────────────────────────────────────

    def _build_action_bar(self, parent):
        """Start extraction + Export buttons."""
        action_frame = ctk.CTkFrame(parent, corner_radius=10)
        action_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            action_frame,
            text="⚡  Actions",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 6))

        btn_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 10))

        self.start_btn = ctk.CTkButton(
            btn_row,
            text="🚀  EXTRACT",
            command=self._start_extraction,
            width=150,
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.export_btn = ctk.CTkButton(
            btn_row,
            text="📥  EXPORT",
            command=self._export_results,
            width=130,
            height=40,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#0d8a0d", "#22c55e"),
            hover_color=("#0a6d0a", "#16a34a"),
            state="disabled",
        )
        self.export_btn.pack(side="left", padx=(0, 10))

        # Append mode checkbox
        self.append_cb = ctk.CTkCheckBox(
            btn_row,
            text="Append",
            variable=self.append_var,
            font=ctk.CTkFont(size=11),
            width=80,
            checkbox_width=18,
            checkbox_height=18,
        )
        self.append_cb.pack(side="left")

    # ── Progress ───────────────────────────────────────────────────

    def _build_progress_section(self, parent):
        """Progress bar."""
        self.progress_bar = ctk.CTkProgressBar(
            parent,
            orientation="horizontal",
            height=6,
            corner_radius=3,
        )
        self.progress_bar.pack(fill="x", pady=(5, 5))
        self.progress_bar.set(0)

    # ── Results Section ────────────────────────────────────────────

    def _build_results_section(self, parent):
        """Build results viewer (hidden until extraction completes)."""
        self.results_frame = ctk.CTkFrame(parent, corner_radius=10)
        # Initially hidden — will be packed after extraction

        # Header with title + row count
        header_row = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            header_row,
            text="📊  Extracted Results  —  Click any cell to edit",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self.result_count_label = ctk.CTkLabel(
            header_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.result_count_label.pack(side="right")

        # Thumbnail + table side by side
        content_row = ctk.CTkFrame(self.results_frame, fg_color="transparent")
        content_row.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # Left: thumbnail
        self.thumb_frame = ctk.CTkFrame(content_row, width=180, corner_radius=8)
        self.thumb_frame.pack(side="left", fill="y", padx=(0, 10))
        self.thumb_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.thumb_frame,
            text="🖼️ Preview",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray",
        ).pack(pady=(8, 4))

        self.thumb_label = ctk.CTkLabel(
            self.thumb_frame,
            text="Select a row\nto preview",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        self.thumb_label.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Right: scrollable table
        self.table_scroll = ctk.CTkScrollableFrame(
            content_row,
            corner_radius=8,
            height=200,
        )
        self.table_scroll.pack(side="left", fill="both", expand=True)

    def _populate_results_table(self):
        """Fill the results table with extracted data."""
        # Clear existing entries
        for widget in self.table_scroll.winfo_children():
            widget.destroy()
        self.result_entries = []

        if not self.extracted_data:
            return

        # Determine columns based on source type
        source = self.source_type_var.get()
        if source == "passbook":
            display_cols = PASSBOOK_DISPLAY_COLS
        else:
            display_cols = UPI_DISPLAY_COLS

        # Filter to columns that actually exist in data
        all_cols = list(self.extracted_data[0].keys())
        self.all_result_columns = [c for c in all_cols if c != 'All Extracted Text']
        self.result_columns = [c for c in display_cols if c in all_cols]

        # --- Header row ---
        for col_idx, col_name in enumerate(self.result_columns):
            lbl = ctk.CTkLabel(
                self.table_scroll,
                text=col_name,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#1a73e8", "#8ab4f8"),
                width=120,
                anchor="w",
            )
            lbl.grid(row=0, column=col_idx, padx=2, pady=(2, 4), sticky="w")

        # --- Data rows ---
        for row_idx, record in enumerate(self.extracted_data, start=1):
            row_entries = {}
            for col_idx, col_name in enumerate(self.result_columns):
                value = str(record.get(col_name, ''))

                entry = ctk.CTkEntry(
                    self.table_scroll,
                    width=120,
                    height=30,
                    corner_radius=4,
                    font=ctk.CTkFont(size=11),
                    border_width=1,
                )
                entry.insert(0, value)
                entry.grid(row=row_idx, column=col_idx, padx=2, pady=1, sticky="w")

                # Clicking an entry highlights the row and shows thumbnail
                entry.bind("<FocusIn>", lambda e, idx=row_idx-1: self._on_row_select(idx))

                row_entries[col_name] = entry
            self.result_entries.append(row_entries)

        # Update count label
        self.result_count_label.configure(
            text=f"{len(self.extracted_data)} record{'s' if len(self.extracted_data) != 1 else ''}"
        )

        # Show results frame
        self.results_frame.pack(fill="both", expand=True, pady=(5, 5), before=self.log_section)

    def _on_row_select(self, row_index):
        """Show image thumbnail when a row is selected."""
        if row_index >= len(self.selected_files):
            return

        img_path = self.selected_files[row_index]
        try:
            pil_img = Image.open(img_path)
            # Scale to fit thumbnail frame (max 160px wide, aspect ratio preserved)
            max_w, max_h = 160, 250
            pil_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                   size=pil_img.size)
            self.thumb_label.configure(
                image=ctk_img,
                text="",
            )
            self.thumb_label._ctk_image = ctk_img  # keep reference
        except Exception:
            self.thumb_label.configure(
                image=None,
                text=f"Cannot preview\n{os.path.basename(img_path)}",
            )

    def _read_edited_data(self):
        """Read current values from the editable table, merging with original data."""
        edited = []
        for row_idx, row_entries in enumerate(self.result_entries):
            if row_idx < len(self.extracted_data):
                record = dict(self.extracted_data[row_idx])  # copy original
            else:
                record = {}

            # Overwrite with edited values from table entries
            for col_name, entry_widget in row_entries.items():
                record[col_name] = entry_widget.get().strip()

            # Remove 'All Extracted Text' from export
            record.pop('All Extracted Text', None)
            edited.append(record)
        return edited

    # ── Status Section ─────────────────────────────────────────────

    def _build_status_section(self, parent):
        """Status / log area using a textbox."""
        self.log_section = ctk.CTkFrame(parent, corner_radius=10)
        self.log_section.pack(fill="both", expand=True, pady=(5, 5))

        ctk.CTkLabel(
            self.log_section,
            text="📋  Activity Log",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(10, 4))

        self.log_textbox = ctk.CTkTextbox(
            self.log_section,
            height=90,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self._log("Welcome! Select images or a folder to begin.")

    # ── Footer ─────────────────────────────────────────────────────

    def _build_footer(self, parent):
        """Developer credit bar with LinkedIn link — prominent and always visible."""
        # Separator above footer
        sep = ctk.CTkFrame(parent, height=2, fg_color=("#d0d0d0", "#3a3a3a"))
        sep.pack(fill="x", pady=(6, 0))

        footer_bar = ctk.CTkFrame(parent, fg_color="transparent", height=36)
        footer_bar.pack(fill="x", pady=(4, 2))

        # Left: version/app info
        ctk.CTkLabel(
            footer_bar,
            text="UPI Payment Extractor  v2.0",
            font=ctk.CTkFont(size=10),
            text_color=("#888888", "#888888"),
        ).pack(side="left")

        # Right: Developer credit — clickable
        credit_frame = ctk.CTkFrame(footer_bar, fg_color="transparent")
        credit_frame.pack(side="right")

        dev_text = ctk.CTkLabel(
            credit_frame,
            text="Developed by  ",
            font=ctk.CTkFont(size=11),
            text_color=("#666666", "#aaaaaa"),
        )
        dev_text.pack(side="left")

        name_label = ctk.CTkLabel(
            credit_frame,
            text="Zala Nirbhay",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1a73e8", "#8ab4f8"),
            cursor="hand2",
        )
        name_label.pack(side="left")

        linkedin_icon = ctk.CTkLabel(
            credit_frame,
            text="  🔗",
            font=ctk.CTkFont(size=13),
            cursor="hand2",
        )
        linkedin_icon.pack(side="left")

        # Bind click on name AND icon
        def open_linkedin(e):
            webbrowser.open("https://www.linkedin.com/in/zala-nirbhay-528a532b0")

        name_label.bind("<Button-1>", open_linkedin)
        linkedin_icon.bind("<Button-1>", open_linkedin)

        # Hover effect on name
        def on_enter(e):
            name_label.configure(text_color=("#0d47a1", "#bbdefb"))
        def on_leave(e):
            name_label.configure(text_color=("#1a73e8", "#8ab4f8"))

        name_label.bind("<Enter>", on_enter)
        name_label.bind("<Leave>", on_leave)

    # ══════════════════════════════════════════════════════════════════
    #  EVENT HANDLERS
    # ══════════════════════════════════════════════════════════════════

    def _toggle_theme(self):
        """Switch between light and dark mode."""
        mode = self.theme_var.get()
        ctk.set_appearance_mode(mode)

    def _log(self, message):
        """Append a timestamped message to the activity log."""
        self.log_textbox.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.insert(END, f"[{timestamp}]  {message}\n")
        self.log_textbox.see(END)
        self.log_textbox.configure(state="disabled")

    def _select_images(self):
        """Open file dialog to select individual image files."""
        files = filedialog.askopenfilenames(
            title="Select Payment Screenshots",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")],
        )
        if files:
            self.selected_files = list(files)
            self._update_file_label()

    def _select_folder(self):
        """Open folder dialog and scan for images recursively."""
        folder = filedialog.askdirectory(title="Select Folder Containing Images")
        if folder:
            self.selected_files = load_images_from_folder(folder)
            self._update_file_label()

    def _update_file_label(self):
        """Update the file count label and enable/disable start button."""
        count = len(self.selected_files)
        if count > 0:
            self.files_label.configure(
                text=f"✅  {count} image{'s' if count != 1 else ''} ready",
                text_color=("#0d8a0d", "#4ade80"),
            )
            self.start_btn.configure(state="normal")
            self._log(f"Selected {count} image(s).")
        else:
            self.files_label.configure(
                text="No files selected",
                text_color="gray",
            )
            self.start_btn.configure(state="disabled")

    def _browse_output(self):
        """Open save-as dialog for Excel output path."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="payment_details.xlsx",
            title="Save Output Excel As",
        )
        if file_path:
            self.output_path_var.set(file_path)
            self._log(f"Output path: {os.path.basename(file_path)}")

    # ── Extraction ─────────────────────────────────────────────────

    def _start_extraction(self):
        """Validate inputs and start extraction in a background thread."""
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select images first.")
            return

        # Disable button, reset progress
        self.start_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._log("Starting extraction process...")

        # Hide old results
        self.results_frame.pack_forget()

        # Run in background thread to keep UI responsive
        thread = threading.Thread(
            target=self._extraction_thread,
            daemon=True,
        )
        thread.start()

    def _extraction_thread(self):
        """Background thread: run extraction pipeline (OCR + parse only)."""
        try:
            source_type = self.source_type_var.get()
            self.extracted_data, self.processing_summary = self.extractor.extract_all(
                self.selected_files,
                progress_callback=self._update_progress,
                source_type=source_type,
            )
            self.after(0, lambda: self._extraction_complete(True, "Extraction complete!"))
        except Exception as e:
            self.after(0, lambda: self._extraction_complete(False, str(e)))

    def _update_progress(self, current, total, message):
        """Callback from extractor — update progress bar and log."""
        progress = current / total
        self.after(0, lambda: self.progress_bar.set(progress))

        if total <= 5 or current % 5 == 0 or current == total:
            self.after(0, lambda: self._log(f"[{current}/{total}] {message}"))

    def _extraction_complete(self, success, message):
        """Handle extraction completion — show results table."""
        self.start_btn.configure(state="normal")

        if success and self.extracted_data:
            s = self.processing_summary
            summary_line = (
                f"✅ {s.get('success', 0)} OK"
                f" · ⏭️ {s.get('duplicates', 0)} duplicates"
                f" · ❌ {s.get('failed', 0)} failed"
            )
            self._log(f"{message} — {summary_line}")
            self._populate_results_table()
            self.export_btn.configure(state="normal")
            self._log("Review results below. Edit cells if needed, then click EXPORT.")
            # Show errors if any
            for fname, err in s.get('errors', []):
                self._log(f"  ⚠️ {fname}: {err}")
        else:
            self._log(f"❌ {message}")
            messagebox.showerror("❌ Error", message)

    # ── Export ─────────────────────────────────────────────────────

    def _export_results(self):
        """Export (possibly edited) results to Excel."""
        output_path = self.output_path_var.get().strip()
        if not output_path:
            messagebox.showwarning("Invalid Path", "Please select a valid output path.")
            return

        # Read edited data from table
        data_to_export = self._read_edited_data()
        append_mode = self.append_var.get()

        if not data_to_export:
            messagebox.showwarning("No Data", "No extracted data to export.")
            return

        mode_str = "Appending" if append_mode else "Exporting"
        self._log(f"{mode_str} to Excel...")
        success, msg = export_to_excel(data_to_export, output_path, append=append_mode)

        if success:
            self._log(f"✅ {msg}")
            messagebox.showinfo("✅ Success", msg)
            try:
                os.startfile(os.path.dirname(output_path))
            except Exception:
                pass
        else:
            self._log(f"❌ {msg}")
            messagebox.showerror("❌ Error", msg)
