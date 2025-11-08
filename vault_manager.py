import os
import hashlib
from cryptography.fernet import Fernet
from datetime import datetime
import json

from flask import jsonify, send_file


# Set consistent vault path (absolute)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DIR = os.path.join(BASE_DIR, "vault")
DECRYPT_DIR = os.path.join(BASE_DIR, "restored")

# Ensure folders exist
os.makedirs(VAULT_DIR, exist_ok=True)
os.makedirs(DECRYPT_DIR, exist_ok=True)

# Example key (replace this with your own key management logic)
KEY_PATH = os.path.join(BASE_DIR, "vault_key.key")
if os.path.exists(KEY_PATH):
    with open(KEY_PATH, "rb") as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)

fernet = Fernet(key)




# ---------- CONFIG ----------
VAULT_DIR = "vault"
KEY_FILE = "vault_key.key"
METADATA_FILE = "vault_metadata.json"

# Ensure vault directory exists
os.makedirs(VAULT_DIR, exist_ok=True)

# ---------- KEY MANAGEMENT ----------
def generate_key():
    """Generate a symmetric encryption key (AES-128 via Fernet)."""
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as key_file:
        key_file.write(key)
    return key

def load_key():
    """Load the encryption key, or generate if missing."""
    if not os.path.exists(KEY_FILE):
        return generate_key()
    return open(KEY_FILE, 'rb').read()

# Load encryption key
fernet = Fernet(load_key())

# ---------- FILE OPERATIONS ----------
def encrypt_and_store(file_path):
    """Encrypt a file and store it in the vault."""
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found.")

    with open(file_path, 'rb') as f:
        data = f.read()

    encrypted = fernet.encrypt(data)
    file_name = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    encrypted_name = f"{file_name}_{timestamp}.enc"

    encrypted_path = os.path.join(VAULT_DIR, encrypted_name)
    with open(encrypted_path, 'wb') as ef:
        ef.write(encrypted)

    # Generate hash for integrity verification
    file_hash = hashlib.sha256(encrypted).hexdigest()

    # Save metadata
    meta_entry = {
        "file_name": file_name,
        "encrypted_file": encrypted_name,
        "timestamp": timestamp,
        "sha256": file_hash
    }
    save_metadata(meta_entry)
    return meta_entry

def decrypt_file(filename):
    """Locate, decrypt, and save restored file"""
    filepath = os.path.join(VAULT_DIR, filename)
    if not os.path.exists(filepath):
        print(f"[DEBUG] File not found at: {filepath}")
        return None

    restored_path = os.path.join(DECRYPT_DIR, filename.replace(".enc", "_restored.txt"))

    try:
        with open(filepath, "rb") as enc_file:
            encrypted_data = enc_file.read()
            decrypted_data = fernet.decrypt(encrypted_data)

        with open(restored_path, "wb") as dec_file:
            dec_file.write(decrypted_data)

        print(f"[INFO] Restored file saved to: {restored_path}")
        return restored_path

    except Exception as e:
        print(f"[ERROR] Decryption failed: {e}")
        return None

# ---------- METADATA MANAGEMENT ----------
def save_metadata(entry):
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'w') as f:
            json.dump([], f)

    with open(METADATA_FILE, 'r') as f:
        data = json.load(f)
    data.append(entry)

    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def list_vault_files():
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, 'r') as f:
        return json.load(f)
