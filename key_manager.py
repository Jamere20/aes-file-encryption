"""
core/key_manager.py
--------------------
Key Generation & Key Encryption (Key Wrapping)

Handles:
  - Generating new random AES private keys
  - Saving/loading keys to/from files
  - Encrypting (wrapping) the private key itself using a passphrase
  - Validating key files
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


SALT_SIZE      = 16
NONCE_SIZE     = 12
KEY_SIZE       = 32   
KDF_ITERATIONS = 200_000



# KEY GENERATION


def generate_aes_key() -> bytes:
    return os.urandom(KEY_SIZE)


def save_key_to_file(key: bytes, file_path: str, as_base64: bool = True) -> None:
    with open(file_path, "wb") as f:
        if as_base64:
            f.write(base64.b64encode(key))
        else:
            f.write(key)


def load_key_from_file(file_path: str) -> bytes:
    with open(file_path, "rb") as f:
        raw = f.read().strip()

    # Try Base64 decode first
    try:
        decoded = base64.b64decode(raw)
        if len(decoded) == KEY_SIZE:
            return decoded
    except Exception:
        pass

    # Fall back to raw binary
    if len(raw) == KEY_SIZE:
        return raw

    raise ValueError(
        f"Invalid key file: expected {KEY_SIZE} bytes but got {len(raw)}. "
        "Make sure you selected the correct .key file."
    )



# KEY WRAPPING (encrypting the key itself)


def wrap_key_with_passphrase(raw_key: bytes, passphrase: str, output_path: str) -> None:
    salt  = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)

    # Derive a key-encrypting-key (KEK) from the passphrase
    kek = _derive_kek(passphrase, salt)

    # Encrypt the raw AES key using the KEK
    aesgcm = AESGCM(kek)
    wrapped = aesgcm.encrypt(nonce, raw_key, associated_data=None)

    with open(output_path, "wb") as f:
        f.write(salt)
        f.write(nonce)
        f.write(wrapped)


def unwrap_key_with_passphrase(wrapped_key_path: str, passphrase: str) -> bytes:
    with open(wrapped_key_path, "rb") as f:
        salt    = f.read(SALT_SIZE)
        nonce   = f.read(NONCE_SIZE)
        wrapped = f.read()

    kek    = _derive_kek(passphrase, salt)
    aesgcm = AESGCM(kek)

    # Will raise InvalidTag if passphrase is wrong
    raw_key = aesgcm.decrypt(nonce, wrapped, associated_data=None)
    return raw_key



# VALIDATION


def validate_key_file(file_path: str) -> tuple[bool, str]:
    """
    Checks whether a file looks like a valid AES key file.

    Returns:
        (True, "OK") if valid, or (False, "reason") if not.
    """
    if not os.path.exists(file_path):
        return False, "File does not exist."
    if os.path.getsize(file_path) == 0:
        return False, "Key file is empty."

    try:
        load_key_from_file(file_path)
        return True, "OK"
    except ValueError as e:
        return False, str(e)


def get_key_info(file_path: str) -> dict:
    """
    Returns metadata about a key file.

    Returns:
        dict with: file_name, file_size, is_base64, is_valid
    """
    name      = os.path.basename(file_path)
    size      = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    is_valid, msg = validate_key_file(file_path)

    with open(file_path, "rb") as f:
        raw = f.read().strip()
    try:
        base64.b64decode(raw)
        is_b64 = True
    except Exception:
        is_b64 = False

    return {
        "file_name": name,
        "file_size": size,
        "is_base64": is_b64,
        "is_valid":  is_valid,
        "message":   msg,
    }



# PRIVATE HELPERS


def _derive_kek(passphrase: str, salt: bytes) -> bytes:
    """Derives a Key Encrypting Key (KEK) from a passphrase using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))
