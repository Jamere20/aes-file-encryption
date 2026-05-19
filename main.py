"""
AES File Encryptor - Main Entry Point
Group Project: Encryption using AES

Run this file to launch the application.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_window import AESEncryptorApp


def main():
    app = AESEncryptorApp()
    app.run()


if __name__ == "__main__":
    main()
