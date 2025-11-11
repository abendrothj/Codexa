"""AES-256 encryption utilities for securing document content."""

from typing import Tuple
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64


class AESEncryption:
    """AES-256 encryption handler."""

    def __init__(self, key: bytes) -> None:
        """
        Initialize encryption with a 256-bit key.

        Args:
            key: 32-byte encryption key for AES-256
        """
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        self.key = key

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a random 256-bit encryption key.

        Returns:
            32-byte random key
        """
        return os.urandom(32)

    def encrypt(self, plaintext: str) -> Tuple[bytes, bytes]:
        """
        Encrypt plaintext using AES-256-CBC.

        Args:
            plaintext: Text to encrypt

        Returns:
            Tuple of (initialization_vector, ciphertext)
        """
        # Generate random IV
        iv = os.urandom(16)

        # Pad plaintext to block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()

        # Encrypt
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return iv, ciphertext

    def decrypt(self, iv: bytes, ciphertext: bytes) -> str:
        """
        Decrypt ciphertext using AES-256-CBC.

        Args:
            iv: Initialization vector
            ciphertext: Encrypted data

        Returns:
            Decrypted plaintext
        """
        # Decrypt
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        return plaintext.decode()

    def encrypt_to_base64(self, plaintext: str) -> str:
        """
        Encrypt and encode to base64 for storage.

        Args:
            plaintext: Text to encrypt

        Returns:
            Base64-encoded string containing IV and ciphertext
        """
        iv, ciphertext = self.encrypt(plaintext)
        combined = iv + ciphertext
        return base64.b64encode(combined).decode()

    def decrypt_from_base64(self, encoded: str) -> str:
        """
        Decrypt from base64-encoded string.

        Args:
            encoded: Base64-encoded IV + ciphertext

        Returns:
            Decrypted plaintext
        """
        combined = base64.b64decode(encoded.encode())
        iv = combined[:16]
        ciphertext = combined[16:]
        return self.decrypt(iv, ciphertext)
