"""
utils/config.py
----------------
Saves and loads user settings (Gmail address, app password) to a local JSON file.

The config file is stored at: ~/.aes_encryptor_config.json
"""

import json
import os

CONFIG_FILE = os.path.expanduser("~/.aes_encryptor_config.json")

DEFAULT_CONFIG = {
    "gmail_address": "",
    "app_password":  "",
}


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults so missing keys don't cause KeyErrors
        config = DEFAULT_CONFIG.copy()
        config.update(data)
        return config
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def clear_config() -> None:
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
