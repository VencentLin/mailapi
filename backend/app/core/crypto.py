"""Symmetric encryption for sensitive values (refresh tokens, etc.)."""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken


class TokenCipher:
    """Encrypt/decrypt short secrets using Fernet (AES-128-CBC + HMAC).

    The *key* string is derived to a 32-byte Fernet key via SHA-256 hashing
    and base64-urlsafe encoding, so callers can pass any reasonably long
    string without worrying about the Fernet key format.
    """

    def __init__(self, key: str) -> None:
        import hashlib

        digest = hashlib.sha256(key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> str:
        """Return an opaque encrypted token string."""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a value previously produced by :meth:`encrypt`.

        Raises :class:`ValueError` if *ciphertext* is not valid.
        """
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid or corrupted ciphertext") from exc
