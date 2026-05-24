"""Secrets encryption utility for .env values.

Usage:
    # Encrypt a value
    python -m app.utils.secrets encrypt "your-api-key-here"

    # Decrypt a value
    python -m app.utils.secrets decrypt "ENC:gAAAAABm..."

    # Encrypt all sensitive values in .env interactively
    python -m app.utils.secrets setup
"""

import base64
import hashlib
import os
import sys
from cryptography.fernet import Fernet


MASTER_KEY_FILE = ".master_key"


def _get_or_create_master_key() -> bytes:
    """Get or create a master encryption key stored locally."""
    key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), MASTER_KEY_FILE)

    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        # Set restrictive permissions
        os.chmod(key_path, 0o600)
        print(f"🔑 Master key created: {key_path}")
        print("⚠️  Keep this file safe! Add .master_key to .gitignore")
        return key


def encrypt_value(value: str) -> str:
    """Encrypt a string value."""
    key = _get_or_create_master_key()
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    return f"ENC:{encrypted.decode()}"


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an ENC: prefixed value."""
    if not encrypted_value.startswith("ENC:"):
        return encrypted_value  # Not encrypted, return as-is

    key = _get_or_create_master_key()
    f = Fernet(key)
    token = encrypted_value[4:]  # Remove "ENC:" prefix
    return f.decrypt(token.encode()).decode()


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted."""
    return value.startswith("ENC:")


def setup_env_encryption():
    """Interactively encrypt sensitive values in .env file."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")

    if not os.path.exists(env_path):
        print("❌ .env file not found")
        return

    sensitive_keys = [
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PORTKEY_API_KEY", "GEMINI_API_KEY",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
        "KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN",
    ]

    lines = []
    with open(env_path, "r") as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()

            if key in sensitive_keys and value and not is_encrypted(value) and not value.startswith("your_"):
                encrypted = encrypt_value(value)
                new_lines.append(f"{key}={encrypted}\n")
                print(f"🔒 Encrypted: {key}")
                updated = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if updated:
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        print("\n✅ .env updated with encrypted values")
    else:
        print("ℹ️  No values to encrypt (already encrypted or placeholders)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m app.utils.secrets encrypt <value>")
        print("  python -m app.utils.secrets decrypt <ENC:value>")
        print("  python -m app.utils.secrets setup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "encrypt":
        value = sys.argv[2] if len(sys.argv) > 2 else input("Value to encrypt: ")
        print(encrypt_value(value))
    elif command == "decrypt":
        value = sys.argv[2] if len(sys.argv) > 2 else input("Value to decrypt: ")
        print(decrypt_value(value))
    elif command == "setup":
        setup_env_encryption()
    else:
        print(f"Unknown command: {command}")
