from vault_manager import encrypt_and_store, decrypt_file, list_vault_files

# Create a sample text file
with open("sample.txt", "w") as f:
    f.write("Confidential backup data")

# Encrypt and store it
meta = encrypt_and_store("sample.txt")
print("Stored:", meta)

# List all vault files
print("Vault contents:", list_vault_files())

# Decrypt the latest file
restored = decrypt_file(meta["encrypted_file"])
print("Restored to:", restored)
