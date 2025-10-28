import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import secrets
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    def __init__(self):
        self.token_fernet = self._create_fernet(settings.TOKEN_ENCRYPTION_KEY)
        self.data_fernet = self._create_fernet(settings.DATA_ENCRYPTION_KEY)
        
    def _create_fernet(self, password: str) -> Fernet:
        """Create Fernet instance from password"""
        salt = b'finhealth360_secure_salt_'  # In production, store separately
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt_token(self, text: str) -> str:
        """Encrypt sensitive tokens (access tokens, etc.)"""
        try:
            return self.token_fernet.encrypt(text.encode()).decode()
        except Exception as e:
            logger.error(f"Token encryption failed: {e}")
            raise ValueError("Encryption failed")
    
    def decrypt_token(self, encrypted_text: str) -> str:
        """Decrypt sensitive tokens"""
        try:
            return self.token_fernet.decrypt(encrypted_text.encode()).decode()
        except InvalidTag:
            logger.error("Token decryption failed - invalid tag")
            raise ValueError("Decryption failed - invalid token")
        except Exception as e:
            logger.error(f"Token decryption failed: {e}")
            raise ValueError("Decryption failed")
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt general data"""
        try:
            return self.data_fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Data encryption failed: {e}")
            raise ValueError("Data encryption failed")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt general data"""
        try:
            return self.data_fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Data decryption failed: {e}")
            raise ValueError("Data decryption failed")

class AESGCMEncryption:
    """Advanced encryption using AES-GCM for highly sensitive data"""
    
    def __init__(self, key: str):
        self.key = self._derive_key(key)
    
    def _derive_key(self, password: str) -> bytes:
        salt = b'finhealth360_aes_salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def encrypt(self, plaintext: str) -> dict:
        """Encrypt using AES-GCM"""
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'nonce': base64.b64encode(nonce).decode()
        }
    
    def decrypt(self, encrypted_data: dict) -> str:
        """Decrypt using AES-GCM"""
        aesgcm = AESGCM(self.key)
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        nonce = base64.b64decode(encrypted_data['nonce'])
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode()

# Initialize encryption services
encryption_service = EncryptionService()
aes_encryption = AESGCMEncryption(settings.DATA_ENCRYPTION_KEY)