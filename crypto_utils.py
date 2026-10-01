import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Constants
SALT_SIZE = 16          # 128-bit salt
NONCE_SIZE = 12         # 96-bit nonce recommended for AES-GCM
PBKDF2_ITERATIONS = 600000  # OWASP recommended iteration count

def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derives a 256-bit AES key from the master password and salt using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS
    )
    return kdf.derive(master_password.encode('utf-8'))

def encrypt_data(plaintext: str, key: bytes) -> bytes:
    """Encrypts plaintext string using AES-256-GCM. Returns combined nonce + ciphertext."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return nonce + ciphertext  # Prepend nonce so it can be extracted during decryption

def decrypt_data(encrypted_data: bytes, key: bytes) -> str:
    """Decrypts AES-256-GCM encrypted bytes using the derived key."""
    nonce = encrypted_data[:NONCE_SIZE]
    ciphertext = encrypted_data[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return decrypted_bytes.decode('utf-8')