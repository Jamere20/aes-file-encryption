"""
core/aes_encryption.py
-----------------------
AES Encryption / Decryption Logic

Handles all AES-GCM encryption and decryption of files.

AES-GCM is used because it provides:
  - Confidentiality (encryption)
  - Integrity (authentication tag)
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

# --- Constants ---
SALT_SIZE   = 16   # bytes - random salt for key derivation
NONCE_SIZE  = 12   # bytes - AES-GCM standard nonce size
TAG_SIZE    = 16   # bytes - AES-GCM authentication tag 
KEY_SIZE    = 32   # bytes - AES-256
KDF_ITERATIONS = 200_000  # PBKDF2 iteration count



# KEY DERIVATION


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def derive_key_from_keyfile(key_file_path: str, salt: bytes) -> bytes:
    with open(key_file_path, "rb") as f:
        raw_key_data = f.read()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(raw_key_data)



# ENCRYPTION


def encrypt_file(input_file_path: str, output_file_path: str, aes_key: bytes) -> dict:
    # Generate a fresh random nonce for this encryption
    nonce = os.urandom(NONCE_SIZE)

    # Read plaintext
    with open(input_file_path, "rb") as f:
        plaintext = f.read()

    # Encrypt using AES-GCM
    # The library automatically appends the 16-byte auth tag to the ciphertext
    aesgcm = AESGCM(aes_key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # Write output: SALT is already embedded in the .enc file by the caller,
    # here we embed: NONCE + CIPHERTEXT_WITH_TAG
    with open(output_file_path, "wb") as f:
        f.write(nonce)
        f.write(ciphertext_with_tag)

    return {
        "nonce": nonce,
        "output_path": output_file_path,
        "original_size": len(plaintext),
        "encrypted_size": os.path.getsize(output_file_path),
    }


def encrypt_file_with_password(input_file_path: str, output_file_path: str, password: str) -> dict:
    salt = os.urandom(SALT_SIZE)
    aes_key = derive_key_from_password(password, salt)

    # Temporarily encrypt without salt in file, then prepend salt
    temp_path = output_file_path + ".tmp"
    result = encrypt_file(input_file_path, temp_path, aes_key)

    # Prepend salt to the final .enc file
    with open(temp_path, "rb") as f:
        enc_data = f.read()
    os.remove(temp_path)

    with open(output_file_path, "wb") as f:
        f.write(salt)           # 16 bytes
        f.write(enc_data)       # NONCE + CIPHERTEXT_WITH_TAG

    result["salt"] = salt
    result["output_path"] = output_file_path
    result["encrypted_size"] = os.path.getsize(output_file_path)
    return result


def encrypt_file_with_keyfile(input_file_path: str, output_file_path: str, key_file_path: str) -> dict:
    salt = os.urandom(SALT_SIZE)
    aes_key = derive_key_from_keyfile(key_file_path, salt)

    temp_path = output_file_path + ".tmp"
    result = encrypt_file(input_file_path, temp_path, aes_key)

    with open(temp_path, "rb") as f:
        enc_data = f.read()
    os.remove(temp_path)

    with open(output_file_path, "wb") as f:
        f.write(salt)
        f.write(enc_data)

    result["salt"] = salt
    result["output_path"] = output_file_path
    result["encrypted_size"] = os.path.getsize(output_file_path)
    return result



# DECRYPTION


def decrypt_file_with_keyfile(enc_file_path: str, output_file_path: str, key_file_path: str) -> bool:
    with open(enc_file_path, "rb") as f:
        salt           = f.read(SALT_SIZE)
        nonce          = f.read(NONCE_SIZE)
        ciphertext_tag = f.read()

    aes_key = derive_key_from_keyfile(key_file_path, salt)
    aesgcm  = AESGCM(aes_key)

    plaintext = aesgcm.decrypt(nonce, ciphertext_tag, associated_data=None)

    with open(output_file_path, "wb") as f:
        f.write(plaintext)

    return True


def decrypt_file_with_password(enc_file_path: str, output_file_path: str, password: str) -> bool:
    with open(enc_file_path, "rb") as f:
        salt             = f.read(SALT_SIZE)
        nonce            = f.read(NONCE_SIZE)
        ciphertext_tag   = f.read()          # rest = ciphertext + 16-byte auth tag

    aes_key = derive_key_from_password(password, salt)
    aesgcm  = AESGCM(aes_key)

    # Will raise InvalidTag if key is wrong or file tampered with
    plaintext = aesgcm.decrypt(nonce, ciphertext_tag, associated_data=None)

    with open(output_file_path, "wb") as f:
        f.write(plaintext)

    return True
