"""
gui/app_window.py
------------------
Tkinter GUI

Provides the full user interface for the AES File Encryptor:
  - Tab 1: Encrypt & Send  (file picker, key picker, email form, send button)
  - Tab 2: Key Generator   (generate and save new AES keys)
  - Tab 3: Settings        (saved Gmail credentials)

The GUI calls into:
  - core/aes_encryption.py  → encrypt the file
  - core/key_manager.py     → load/validate the key
  - email_handler/gmail_sender.py → send the email
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os

from aes_encryption import (
    encrypt_file_with_keyfile, encrypt_file_with_password,
    decrypt_file_with_password, decrypt_file_with_keyfile,
)
from key_manager import generate_aes_key, save_key_to_file, validate_key_file, get_key_info
from gmail_sender import (
    send_encrypted_file,
    test_connection,
    validate_email_address,
    validate_app_password,
)
from file_utils import get_file_size_str, get_output_path
from config import load_config, save_config



# MAIN APPLICATION CLASS


class AESEncryptorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AES File Encryptor")
        self.root.geometry("700x560")
        self.root.resizable(False, False)

        # Load saved config (Gmail address, etc.)
        self.config = load_config()

        # Apply a clean theme
        self._apply_theme()

        # Build UI
        self._build_header()
        self._build_tabs()
        self._build_status_bar()

   
    # SETUP
    

    def _apply_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        self.root.configure(bg="#1e1e2e")

        style.configure("TNotebook",        background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab",    background="#2a2a3d", foreground="#cdd6f4",
                        padding=[14, 6],    font=("Helvetica", 10, "bold"))
        style.map("TNotebook.Tab",          background=[("selected", "#313244")])

        style.configure("TFrame",           background="#1e1e2e")
        style.configure("TLabel",           background="#1e1e2e", foreground="#cdd6f4",
                        font=("Helvetica", 10))
        style.configure("TButton",          background="#89b4fa", foreground="#1e1e2e",
                        font=("Helvetica", 10, "bold"), padding=6)
        style.map("TButton",                background=[("active", "#74c7ec")])
        style.configure("TEntry",           fieldbackground="#313244", foreground="#cdd6f4",
                        insertcolor="#cdd6f4", borderwidth=1)
        style.configure("Accent.TButton",   background="#a6e3a1", foreground="#1e1e2e",
                        font=("Helvetica", 11, "bold"), padding=8)
        style.map("Accent.TButton",         background=[("active", "#94e2d5")])
        style.configure("Danger.TButton",   background="#f38ba8", foreground="#1e1e2e",
                        font=("Helvetica", 10, "bold"))

    def _build_header(self):
        header = tk.Frame(self.root, bg="#313244", height=60)
        header.pack(fill="x")
        tk.Label(
            header,
            text="AES File Encryptor",
            bg="#313244", fg="#cdd6f4",
            font=("Helvetica", 16, "bold"),
        ).pack(side="left", padx=20, pady=12)

        tk.Label(
            header,
            text="Secure • Private • AES",
            bg="#313244", fg="#6c7086",
            font=("Helvetica", 9),
        ).pack(side="right", padx=20)

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab frames
        self.tab_encrypt  = ttk.Frame(self.notebook, padding=16)
        self.tab_decrypt  = ttk.Frame(self.notebook, padding=16)
        self.tab_keygen   = ttk.Frame(self.notebook, padding=16)
        self.tab_settings = ttk.Frame(self.notebook, padding=16)

        self.notebook.add(self.tab_encrypt,  text="  Encrypt & Send  ")
        self.notebook.add(self.tab_decrypt,  text="  Decrypt File  ")
        self.notebook.add(self.tab_keygen,   text="  Key Generator  ")
        self.notebook.add(self.tab_settings, text="  Settings  ")

        self._build_encrypt_tab()
        self._build_decrypt_tab()
        self._build_keygen_tab()
        self._build_settings_tab()

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="Ready.")
        bar = tk.Frame(self.root, bg="#181825", height=28)
        bar.pack(fill="x", side="bottom")
        tk.Label(
            bar, textvariable=self.status_var,
            bg="#181825", fg="#6c7086",
            font=("Helvetica", 9), anchor="w",
        ).pack(side="left", padx=12, pady=4)


    # TAB 1: ENCRYPT & SEND
   

    def _build_encrypt_tab(self):
        tab = self.tab_encrypt

        # File Selection 
        self._section_label(tab, "1. Select File to Encrypt", row=0)

        self.file_path_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.file_path_var, width=52).grid(
            row=1, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(tab, text="Browse…", command=self._browse_file).grid(
            row=1, column=1, padx=(8, 0))

        self.file_info_var = tk.StringVar(value="No file selected.")
        ttk.Label(tab, textvariable=self.file_info_var,
                  foreground="#6c7086", font=("Helvetica", 8)).grid(
            row=2, column=0, sticky="w", pady=(0, 10))

        # Key Selection 
        self._section_label(tab, "2. Select Private Key", row=3)

        # Key source: file or password
        self.key_mode = tk.StringVar(value="file")
        key_mode_frame = ttk.Frame(tab)
        key_mode_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Radiobutton(key_mode_frame, text="Key File  ", variable=self.key_mode,
                        value="file",     command=self._toggle_key_mode).pack(side="left")
        ttk.Radiobutton(key_mode_frame, text="Password  ", variable=self.key_mode,
                        value="password", command=self._toggle_key_mode).pack(side="left")

        # Key file row
        self.key_file_frame = ttk.Frame(tab)
        self.key_file_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.key_path_var = tk.StringVar()
        ttk.Entry(self.key_file_frame, textvariable=self.key_path_var, width=52).pack(
            side="left")
        ttk.Button(self.key_file_frame, text="Browse…",
                   command=self._browse_key_file).pack(side="left", padx=(8, 0))

        # Password row (hidden by default)
        self.key_pass_frame = ttk.Frame(tab)
        self.key_pass_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Label(self.key_pass_frame, text="Password:").pack(side="left")
        self.key_password_var = tk.StringVar()
        ttk.Entry(self.key_pass_frame, textvariable=self.key_password_var,
                  show="●", width=38).pack(side="left", padx=(8, 0))
        self.key_pass_frame.grid_remove()   # hidden initially

        self.key_info_var = tk.StringVar(value="No key selected.")
        ttk.Label(tab, textvariable=self.key_info_var,
                  foreground="#6c7086", font=("Helvetica", 8)).grid(
            row=7, column=0, sticky="w", pady=(2, 10))

        #  Email Form 
        self._section_label(tab, "3. Send Encrypted File", row=8)

        ttk.Label(tab, text="Recipient Email:").grid(row=9, column=0, sticky="w")
        self.recipient_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.recipient_var, width=42).grid(
            row=10, column=0, sticky="ew", pady=(2, 6))

        ttk.Label(tab, text="Subject (optional):").grid(row=11, column=0, sticky="w")
        self.subject_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.subject_var, width=42).grid(
            row=12, column=0, sticky="ew", pady=(2, 12))

        # Action Buttons 
        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=13, column=0, columnspan=2, sticky="ew")

        ttk.Button(btn_frame, text="Encrypt Only",
                   command=self._action_encrypt_only).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Encrypt & Send",
                   command=self._action_encrypt_and_send,
                   style="Accent.TButton").pack(side="left")

        # Progress bar (hidden until needed)
        self.progress = ttk.Progressbar(tab, mode="indeterminate", length=400)
        self.progress.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.progress.grid_remove()

        tab.columnconfigure(0, weight=1)

    def _toggle_key_mode(self):
        if self.key_mode.get() == "file":
            self.key_file_frame.grid()
            self.key_pass_frame.grid_remove()
            self.key_info_var.set("No key selected.")
        else:
            self.key_file_frame.grid_remove()
            self.key_pass_frame.grid()
            self.key_info_var.set("Using password-derived key.")

  
    # TAB 2: DECRYPT FILE
    

    def _build_decrypt_tab(self):
        tab = self.tab_decrypt

        self._section_label(tab, "1. Select Encrypted File (.enc)", row=0)

        self.dec_file_path_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.dec_file_path_var, width=52).grid(
            row=1, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(tab, text="Browse…", command=self._browse_dec_file).grid(
            row=1, column=1, padx=(8, 0))

        self.dec_file_info_var = tk.StringVar(value="No file selected.")
        ttk.Label(tab, textvariable=self.dec_file_info_var,
                  foreground="#6c7086", font=("Helvetica", 8)).grid(
            row=2, column=0, sticky="w", pady=(0, 10))

        # Key mode
        self._section_label(tab, "2. Select Private Key", row=3)

        self.dec_key_mode = tk.StringVar(value="file")
        dec_key_mode_frame = ttk.Frame(tab)
        dec_key_mode_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Radiobutton(dec_key_mode_frame, text="Key File  ", variable=self.dec_key_mode,
                        value="file",     command=self._toggle_dec_key_mode).pack(side="left")
        ttk.Radiobutton(dec_key_mode_frame, text="Password  ", variable=self.dec_key_mode,
                        value="password", command=self._toggle_dec_key_mode).pack(side="left")

        # Key file
        self.dec_key_file_frame = ttk.Frame(tab)
        self.dec_key_file_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.dec_key_path_var = tk.StringVar()
        ttk.Entry(self.dec_key_file_frame, textvariable=self.dec_key_path_var, width=52).pack(side="left")
        ttk.Button(self.dec_key_file_frame, text="Browse…",
                   command=self._browse_dec_key_file).pack(side="left", padx=(8, 0))

        # Password
        self.dec_key_pass_frame = ttk.Frame(tab)
        self.dec_key_pass_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Label(self.dec_key_pass_frame, text="Password:").pack(side="left")
        self.dec_key_password_var = tk.StringVar()
        ttk.Entry(self.dec_key_pass_frame, textvariable=self.dec_key_password_var,
                  show="●", width=38).pack(side="left", padx=(8, 0))
        self.dec_key_pass_frame.grid_remove()

        self.dec_key_info_var = tk.StringVar(value="No key selected.")
        ttk.Label(tab, textvariable=self.dec_key_info_var,
                  foreground="#6c7086", font=("Helvetica", 8)).grid(
            row=7, column=0, sticky="w", pady=(2, 10))

        #  Output location 
        self._section_label(tab, "3. Save Decrypted File As", row=8)

        self.dec_output_path_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.dec_output_path_var, width=52).grid(
            row=9, column=0, sticky="ew", pady=(0, 4))
        ttk.Button(tab, text="Browse…", command=self._browse_dec_output).grid(
            row=9, column=1, padx=(8, 0))

        ttk.Label(tab, text="Leave blank to auto-save next to the .enc file.",
                  foreground="#6c7086", font=("Helvetica", 8)).grid(
            row=10, column=0, sticky="w", pady=(0, 14))

        #  Decrypt button 
        ttk.Button(tab, text="Decrypt File",
                   command=self._action_decrypt,
                   style="Accent.TButton").grid(row=11, column=0, sticky="w")

        # Progress bar
        self.dec_progress = ttk.Progressbar(tab, mode="indeterminate", length=400)
        self.dec_progress.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self.dec_progress.grid_remove()

        tab.columnconfigure(0, weight=1)

    def _toggle_dec_key_mode(self):
        if self.dec_key_mode.get() == "file":
            self.dec_key_file_frame.grid()
            self.dec_key_pass_frame.grid_remove()
            self.dec_key_info_var.set("No key selected.")
        else:
            self.dec_key_file_frame.grid_remove()
            self.dec_key_pass_frame.grid()
            self.dec_key_info_var.set("Using password-derived key.")

    # TAB 3: KEY GENERATOR


    def _build_keygen_tab(self):
        tab = self.tab_keygen

        self._section_label(tab, "Generate a New AES-256 Key", row=0)
        ttk.Label(tab, text=(
            "Click the button below to generate a cryptographically secure random key.\n"
            "Save it to a file and share it securely with the recipient."
        ), wraplength=560, justify="left").grid(row=1, column=0, columnspan=2,
                                                sticky="w", pady=(0, 16))

        ttk.Button(tab, text="Generate New Key",
                   command=self._action_generate_key).grid(row=2, column=0, sticky="w")

        self.generated_key_var = tk.StringVar(value="")
        ttk.Label(tab, text="Generated Key (Base64):").grid(row=3, column=0, sticky="w",
                                                             pady=(14, 2))
        key_display = tk.Text(tab, height=3, width=60, state="disabled",
                              bg="#313244", fg="#a6e3a1",
                              font=("Courier", 9), borderwidth=1, relief="flat")
        key_display.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._keydisplay = key_display

        ttk.Button(tab, text="Save Key to File…",
                   command=self._action_save_key).grid(row=5, column=0, sticky="w",
                                                       pady=(10, 0))

        self._generated_key_bytes = None   # stores the raw bytes of last generated key

        tab.columnconfigure(0, weight=1)


    # TAB 3: SETTINGS


    def _build_settings_tab(self):
        tab = self.tab_settings

        self._section_label(tab, "Gmail Account Settings", row=0)
        ttk.Label(tab, text=(
            "Enter your Gmail address and App Password.\n"
            "Get an App Password at: Google Account → Security → App Passwords"
        ), wraplength=560, justify="left").grid(row=1, column=0, columnspan=2,
                                                sticky="w", pady=(0, 14))

        ttk.Label(tab, text="Gmail Address:").grid(row=2, column=0, sticky="w")
        self.settings_email_var = tk.StringVar(value=self.config.get("gmail_address", ""))
        ttk.Entry(tab, textvariable=self.settings_email_var, width=44).grid(
            row=3, column=0, sticky="ew", pady=(2, 8))

        ttk.Label(tab, text="App Password (16 characters):").grid(row=4, column=0, sticky="w")
        self.settings_pass_var = tk.StringVar(value=self.config.get("app_password", ""))
        ttk.Entry(tab, textvariable=self.settings_pass_var, show="●", width=44).grid(
            row=5, column=0, sticky="ew", pady=(2, 14))

        btn_frame = ttk.Frame(tab)
        btn_frame.grid(row=6, column=0, columnspan=2, sticky="w")
        ttk.Button(btn_frame, text="Save Settings",
                   command=self._action_save_settings).pack(side="left", padx=(0, 8))
        ttk.Button(btn_frame, text="Test Connection",
                   command=self._action_test_connection).pack(side="left")

        tab.columnconfigure(0, weight=1)


    # BROWSE ACTIONS
 

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select file to encrypt",
            filetypes=[("All Files", "*.*")]
        )
        if path:
            self.file_path_var.set(path)
            size_str = get_file_size_str(path)
            self.file_info_var.set(f"{os.path.basename(path)}  —  {size_str}")
            self._set_status(f"File selected: {os.path.basename(path)}")

    def _browse_key_file(self):
        path = filedialog.askopenfilename(
            title="Select private key file",
            filetypes=[("Key Files", "*.key"), ("All Files", "*.*")]
        )
        if path:
            self.key_path_var.set(path)
            valid, msg = validate_key_file(path)
            if valid:
                info = get_key_info(path)
                self.key_info_var.set(
                    f"{info['file_name']}  —  {info['file_size']} bytes  ✓ Valid"
                )
            else:
                self.key_info_var.set(f"⚠ {msg}")

    def _browse_dec_file(self):
        path = filedialog.askopenfilename(
            title="Select encrypted file",
            filetypes=[("Encrypted Files", "*.enc"), ("All Files", "*.*")]
        )
        if path:
            self.dec_file_path_var.set(path)
            size_str = get_file_size_str(path)
            self.dec_file_info_var.set(f"{os.path.basename(path)}  —  {size_str}")
            self._set_status(f"Encrypted file selected: {os.path.basename(path)}")

    def _browse_dec_key_file(self):
        path = filedialog.askopenfilename(
            title="Select private key file",
            filetypes=[("Key Files", "*.key"), ("All Files", "*.*")]
        )
        if path:
            self.dec_key_path_var.set(path)
            valid, msg = validate_key_file(path)
            if valid:
                info = get_key_info(path)
                self.dec_key_info_var.set(
                    f"{info['file_name']}  —  {info['file_size']} bytes  ✓ Valid"
                )
            else:
                self.dec_key_info_var.set(f"⚠ {msg}")

    def _browse_dec_output(self):
        enc_path = self.dec_file_path_var.get().strip()
        initial = os.path.basename(enc_path).replace(".enc", "") if enc_path else "decrypted_file"
        path = filedialog.asksaveasfilename(
            title="Save decrypted file as…",
            initialfile=initial,
            filetypes=[("All Files", "*.*")]
        )
        if path:
            self.dec_output_path_var.set(path)

   
    # MAIN ACTIONS
   

    def _action_decrypt(self):
        enc_path = self.dec_file_path_var.get().strip()
        if not enc_path or not os.path.exists(enc_path):
            messagebox.showerror("Error", "Please select a valid .enc file to decrypt.")
            return

        # Determine output path
        output_path = self.dec_output_path_var.get().strip()
        if not output_path:
            # Auto-generate next to the .enc file
            base = enc_path[:-4] if enc_path.endswith(".enc") else enc_path
            name, ext = os.path.splitext(base)
            output_path = f"{name}_decrypted{ext}" if ext else f"{base}_decrypted"

        self._run_dec_in_thread(self._do_decrypt, enc_path, output_path,
                                callback=lambda ok, msg: self._on_decrypt_done(ok, msg, output_path))

    def _do_decrypt(self, enc_path: str, output_path: str) -> tuple[bool, str]:
        """Background worker: decrypt the file."""
        try:
            if self.dec_key_mode.get() == "file":
                key_path = self.dec_key_path_var.get().strip()
                if not key_path:
                    return False, "No key file selected."
                decrypt_file_with_keyfile(enc_path, output_path, key_path)
            else:
                password = self.dec_key_password_var.get()
                if not password:
                    return False, "No password entered."
                decrypt_file_with_password(enc_path, output_path, password)
            return True, output_path
        except Exception as e:
            # InvalidTag means wrong key or corrupted file
            if "InvalidTag" in type(e).__name__:
                return False, "Decryption failed: Wrong key or the file has been corrupted/tampered with."
            return False, f"Decryption error: {str(e)}"

    def _on_decrypt_done(self, ok: bool, msg: str, output_path: str):
        self._hide_dec_progress()
        if ok:
            messagebox.showinfo(
                "Decrypted!",
                f"File decrypted successfully!\n\nSaved to:\n{output_path}"
            )
            self._set_status(f"Decrypted: {os.path.basename(output_path)}")
        else:
            messagebox.showerror("Decryption Failed", msg)
            self._set_status("Decryption failed.")

    def _run_dec_in_thread(self, fn, *args, callback=None):
        self._show_dec_progress()

        def worker():
            result = fn(*args)
            self.root.after(0, self._hide_dec_progress)
            if callback:
                self.root.after(10, lambda: callback(result))

        threading.Thread(target=worker, daemon=True).start()

    def _show_dec_progress(self):
        self.dec_progress.grid()
        self.dec_progress.start(10)

    def _hide_dec_progress(self):
        self.dec_progress.stop()
        self.dec_progress.grid_remove()

    def _action_encrypt_only(self):
        file_path = self.file_path_var.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file to encrypt.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save encrypted file as…",
            defaultextension=".enc",
            initialfile=os.path.basename(file_path) + ".enc",
            filetypes=[("Encrypted Files", "*.enc"), ("All Files", "*.*")],
        )
        if not output_path:
            return

        self._run_in_thread(self._do_encrypt, file_path, output_path,
                            callback=lambda ok, msg: self._on_encrypt_done(ok, msg))

    def _action_encrypt_and_send(self):
        # Validate inputs
        file_path = self.file_path_var.get().strip()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file to encrypt.")
            return

        recipient = self.recipient_var.get().strip()
        ok, msg = validate_email_address(recipient)
        if not ok:
            messagebox.showerror("Invalid Email", msg)
            return

        sender_email = self.settings_email_var.get().strip()
        app_password = self.settings_pass_var.get().strip()
        if not sender_email or not app_password:
            messagebox.showerror(
                "Missing Credentials",
                "Please fill in your Gmail address and App Password in the Settings tab."
            )
            return

        # Choose output path (temp file)
        output_path = get_output_path(file_path)

        self._run_in_thread(
            self._do_encrypt_and_send,
            file_path, output_path, sender_email, app_password, recipient,
            callback=lambda ok, msg: self._on_send_done(ok, msg, output_path),
        )

    def _action_generate_key(self):
        import base64
        key = generate_aes_key()
        self._generated_key_bytes = key

        b64 = base64.b64encode(key).decode()
        self._keydisplay.config(state="normal")
        self._keydisplay.delete("1.0", "end")
        self._keydisplay.insert("1.0", b64)
        self._keydisplay.config(state="disabled")
        self._set_status("New 256-bit AES key generated.")

    def _action_save_key(self):
        if self._generated_key_bytes is None:
            messagebox.showwarning("No Key", "Generate a key first.")
            return

        path = filedialog.asksaveasfilename(
            title="Save key file as…",
            defaultextension=".key",
            initialfile="private.key",
            filetypes=[("Key Files", "*.key"), ("All Files", "*.*")],
        )
        if path:
            save_key_to_file(self._generated_key_bytes, path, as_base64=True)
            messagebox.showinfo("Saved", f"Key saved to:\n{path}")
            self._set_status(f"Key saved: {os.path.basename(path)}")

    def _action_save_settings(self):
        self.config["gmail_address"] = self.settings_email_var.get().strip()
        self.config["app_password"]  = self.settings_pass_var.get().strip()
        save_config(self.config)
        messagebox.showinfo("Saved", "Settings saved successfully.")
        self._set_status("Settings saved.")

    def _action_test_connection(self):
        sender  = self.settings_email_var.get().strip()
        pwd     = self.settings_pass_var.get().strip()
        if not sender or not pwd:
            messagebox.showerror("Missing", "Please enter your Gmail address and App Password.")
            return

        self._set_status("Testing Gmail connection…")
        self._show_progress()
        self._run_in_thread(
            test_connection,
            sender, pwd,
            callback=self._on_test_connection,
        )

   
    # WORKER FUNCTIONS (run in background thread)
   

    def _do_encrypt(self, file_path: str, output_path: str) -> tuple[bool, str]:
        try:
            if self.key_mode.get() == "file":
                key_path = self.key_path_var.get().strip()
                if not key_path:
                    return False, "No key file selected."
                encrypt_file_with_keyfile(file_path, output_path, key_path)
            else:
                password = self.key_password_var.get()
                if not password:
                    return False, "No password entered."
                encrypt_file_with_password(file_path, output_path, password)
            return True, output_path
        except Exception as e:
            return False, str(e)

    def _do_encrypt_and_send(self, file_path, output_path,
                             sender_email, app_password, recipient) -> tuple[bool, str]:
        """Background: encrypt then send."""
        ok, msg = self._do_encrypt(file_path, output_path)
        if not ok:
            return False, msg

        subject = self.subject_var.get().strip() or None
        ok2, msg2 = send_encrypted_file(
            sender_email   = sender_email,
            app_password   = app_password,
            recipient_email= recipient,
            attachment_path= output_path,
            subject        = subject,
        )
        return ok2, msg2

   
    # CALLBACKS (back on main thread)
  

    def _on_encrypt_done(self, ok: bool, msg: str):
        self._hide_progress()
        if ok:
            messagebox.showinfo("Encrypted", f"File encrypted successfully!\n\nSaved to:\n{msg}")
            self._set_status(f"Encrypted: {os.path.basename(msg)}")
        else:
            messagebox.showerror("Encryption Failed", msg)
            self._set_status("Encryption failed.")

    def _on_send_done(self, ok: bool, msg: str, output_path: str):
        self._hide_progress()
        if ok:
            messagebox.showinfo("Sent!", msg)
            self._set_status("Email sent successfully.")
        else:
            messagebox.showerror("Send Failed", msg)
            self._set_status("Send failed.")

    def _on_test_connection(self, result):
        self._hide_progress()
        ok, msg = result
        if ok:
            messagebox.showinfo("Connection OK", msg)
            self._set_status("Gmail connection OK.")
        else:
            messagebox.showerror("Connection Failed", msg)
            self._set_status("Gmail connection failed.")

    
    # THREADING HELPER


    def _run_in_thread(self, fn, *args, callback=None):
        self._show_progress()

        def worker():
            result = fn(*args)
            # Always hide progress first, then fire callback
            self.root.after(0, self._hide_progress)
            if callback:
                self.root.after(10, lambda: callback(result))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

  
    # UI HELPERS
  

    def _section_label(self, parent, text: str, row: int):
        ttk.Label(parent, text=text,
                  font=("Helvetica", 11, "bold"),
                  foreground="#89b4fa").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(10, 4))

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _show_progress(self):
        self.progress.grid()
        self.progress.start(10)

    def _hide_progress(self):
        self.progress.stop()
        self.progress.grid_remove()

   
    # START


    def run(self):
        self.root.mainloop()
