"""Tests for encryption functionality."""

import pytest
from core.crypto import AESEncryption


def test_key_generation() -> None:
    """Test encryption key generation."""
    key = AESEncryption.generate_key()
    assert len(key) == 32
    assert isinstance(key, bytes)


def test_encryption_decryption() -> None:
    """Test basic encryption and decryption."""
    key = AESEncryption.generate_key()
    aes = AESEncryption(key)

    plaintext = "This is a test message"
    iv, ciphertext = aes.encrypt(plaintext)

    assert len(iv) == 16
    assert isinstance(ciphertext, bytes)
    assert len(ciphertext) > 0

    decrypted = aes.decrypt(iv, ciphertext)
    assert decrypted == plaintext


def test_base64_encryption() -> None:
    """Test base64-encoded encryption."""
    key = AESEncryption.generate_key()
    aes = AESEncryption(key)

    plaintext = "Test message with special chars: !@#$%^&*()"
    encoded = aes.encrypt_to_base64(plaintext)

    assert isinstance(encoded, str)
    assert len(encoded) > 0

    decrypted = aes.decrypt_from_base64(encoded)
    assert decrypted == plaintext


def test_invalid_key_length() -> None:
    """Test that invalid key length raises error."""
    with pytest.raises(ValueError, match="Key must be 32 bytes"):
        AESEncryption(b"short_key")


def test_long_text_encryption() -> None:
    """Test encryption of longer text."""
    key = AESEncryption.generate_key()
    aes = AESEncryption(key)

    plaintext = "A" * 10000
    encoded = aes.encrypt_to_base64(plaintext)
    decrypted = aes.decrypt_from_base64(encoded)

    assert decrypted == plaintext
