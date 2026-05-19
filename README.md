# AES File Encryptor
# Group Project — Encryption using AES

# Setup
# 1. Install Python dependencies
pip install -r requirements.txt


# 2. Set up Gmail App Password
Gmail no longer allows regular passwords for SMTP.
You need a Gmail App Password:

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → App Passwords
3. Create one: App = "Mail", Device = "Other (Custom name)"
4. Copy the 16-character password shown

# 3. Run the application
python main.py


# Member Responsibilities
1 - `core/aes_encryption.py` | AES-GCM encrypt/decrypt, PBKDF2 key derivation 
2 - `core/key_manager.py` | Key generation, key wrapping, key file I/O 
3 - `email_handler/gmail_sender.py` | SMTP connection, email composition, send 
4 - Anisa Jakupi `gui/app_window.py` | Tkinter GUI, file pickers, tabs, threading 
