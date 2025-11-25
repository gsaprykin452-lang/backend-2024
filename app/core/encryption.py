"""
Encryption utilities for storing OAuth credentials
"""
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib

# Generate encryption key from SECRET_KEY
def get_encryption_key() -> bytes:
    """Generate encryption key from SECRET_KEY"""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


_fernet = Fernet(get_encryption_key())


def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    return _fernet.encrypt(data.encode()).decode()


def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    return _fernet.decrypt(encrypted_data.encode()).decode()

