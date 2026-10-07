import os
import string
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


# ---------- Master password strength ----------
MIN_PASSWORD_LENGTH = 8
COMMON_PASSWORD_PARTS = ("password", "passw0rd", "123456", "qwerty", "letmein", "admin", "welcome", "iloveyou")

def check_password_strength(password: str) -> dict:
    """
    Evaluates a master password against the vault's rules.
    Returns:
        rules:      [(key, description, passed), ...]
        score:      0.0 - 1.0 (for a progress bar)
        label:      Weak / Fair / Good / Strong / Excellent
        color:      hex colour matching the label
        acceptable: True only when every rule passes
    """
    lowered = password.lower()
    rules = [
        ("length",  f"At least {MIN_PASSWORD_LENGTH} characters",  len(password) >= MIN_PASSWORD_LENGTH),
        ("upper",   "An uppercase letter (A-Z)",                   any(c.isupper() for c in password)),
        ("lower",   "A lowercase letter (a-z)",                    any(c.islower() for c in password)),
        ("number",  "A number (0-9)",                              any(c.isdigit() for c in password)),
        ("special", "A special character (!@#$%...)",              any(c in string.punctuation for c in password)),
        ("common",  "Not a common or easy-to-guess password",      bool(password) and not any(part in lowered for part in COMMON_PASSWORD_PARTS)),
    ]
    met = sum(1 for _, _, ok in rules if ok)
    acceptable = met == len(rules)

    if not password:
        return {"rules": rules, "score": 0.0, "label": "", "color": "gray", "acceptable": False}

    if not acceptable:
        label, color = ("Weak", "#D9534F") if met <= 3 else ("Fair", "#F0AD4E")
        bonus = 0
    elif len(password) >= 16:
        label, color, bonus = "Excellent", "#2FA572", 2
    elif len(password) >= 12:
        label, color, bonus = "Strong", "#2FA572", 1
    else:
        label, color, bonus = "Good", "#3B8ED0", 0

    return {"rules": rules, "score": (met + bonus) / (len(rules) + 2), "label": label,
            "color": color, "acceptable": acceptable}