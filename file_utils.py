"""
utils/file_utils.py
--------------------
Shared file utility functions used across the project.
"""

import os


def get_file_size_str(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "unknown size"

    size = os.path.getsize(file_path)

    if size >= 1_048_576:
        return f"{size / 1_048_576:.2f} MB"
    elif size >= 1_024:
        return f"{size / 1_024:.1f} KB"
    else:
        return f"{size} bytes"


def get_output_path(input_file_path: str, output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.dirname(input_file_path)

    base_name = os.path.basename(input_file_path) + ".enc"
    return os.path.join(output_dir, base_name)


def get_decrypted_output_path(enc_file_path: str) -> str:
    if enc_file_path.endswith(".enc"):
        base = enc_file_path[:-4]
    else:
        base = enc_file_path

    # Avoid overwriting the original — add a suffix
    name, ext = os.path.splitext(base)
    return f"{name}_decrypted{ext}"


def ensure_dir(dir_path: str) -> None:
    os.makedirs(dir_path, exist_ok=True)


def safe_delete(file_path: str) -> bool:
    try:
        os.remove(file_path)
        return True
    except FileNotFoundError:
        return False


def get_file_extension(file_path: str) -> str:
    _, ext = os.path.splitext(file_path)
    return ext.lower()


def is_already_encrypted(file_path: str) -> bool:
    return file_path.lower().endswith(".enc")
