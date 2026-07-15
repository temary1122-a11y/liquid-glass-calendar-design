"""
Phone encryption utilities (Fernet symmetric encryption).

Encrypts/decrypts phone numbers stored in the database.
Uses ENCRYPTION_KEY from config — must be set in production.

Usage:
  from utils.crypto import encrypt_phone, decrypt_phone

  encrypted = encrypt_phone("+79161234567")
  original  = decrypt_phone(encrypted)
"""

import logging

from cryptography.fernet import Fernet

from config import ENCRYPTION_KEY

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    """Lazy-init Fernet instance. Returns None if ENCRYPTION_KEY is not set."""
    global _fernet
    if _fernet is not None:
        return _fernet

    if not ENCRYPTION_KEY:
        logger.warning("ENCRYPTION_KEY not set — phone encryption is DISABLED")
        return None

    try:
        _fernet = Fernet(ENCRYPTION_KEY.encode())
        return _fernet
    except Exception as exc:
        logger.error("Invalid ENCRYPTION_KEY: %s", exc)
        return None


def encrypt_phone(phone: str | None) -> str | None:
    """
    Encrypt a phone number for storage.
    Returns None if phone is None/empty.
    Prefixes with 'enc:' so we can detect already-encrypted values.
    """
    if not phone or not phone.strip():
        return phone

    # Already encrypted (has the marker prefix)
    if phone.startswith("enc:"):
        return phone

    f = _get_fernet()
    if f is None:
        # Fallback: store in plaintext with a warning
        logger.warning("Storing phone in plaintext (ENCRYPTION_KEY not set)")
        return phone

    try:
        encrypted = f.encrypt(phone.encode())
        return "enc:" + encrypted.decode()
    except Exception as exc:
        logger.error("Failed to encrypt phone: %s", exc)
        return phone  # fallback: plaintext


def decrypt_phone(phone: str | None) -> str | None:
    """
    Decrypt a phone number from storage.
    Returns None if phone is None/empty.
    Handles both encrypted ('enc:...') and plaintext values.
    """
    if not phone:
        return phone

    if phone.startswith("enc:"):
        f = _get_fernet()
        if f is None:
            # Can't decrypt — return masked version
            logger.warning("ENCRYPTION_KEY not set, cannot decrypt phone")
            return "***"

        try:
            decrypted = f.decrypt(phone[4:].encode())
            return decrypted.decode()
        except Exception as exc:
            logger.error("Failed to decrypt phone: %s", exc)
            return "***"

    # Plaintext phone (not yet encrypted, or encryption disabled)
    return phone
