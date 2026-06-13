"""Unit tests for TokenCipher — no database or HTTP needed."""

import pytest

from backend.app.core.crypto import TokenCipher


class TestTokenCipher:
    """Verify encrypt/decrypt roundtrip and error handling."""

    def test_encrypted_text_differs_from_plaintext(self):
        cipher = TokenCipher(key="test-key-32-bytes-long!!")
        plain = "a-very-secret-refresh-token"
        encrypted = cipher.encrypt(plain)
        assert encrypted != plain
        assert len(encrypted) > 0

    def test_decrypt_restores_original_plaintext(self):
        cipher = TokenCipher(key="another-key-32-bytes!!!!")
        plain = "refresh-token-value-123"
        encrypted = cipher.encrypt(plain)
        assert cipher.decrypt(encrypted) == plain

    def test_decrypt_with_wrong_key_raises_valueerror(self):
        cipher_a = TokenCipher(key="key-a-32-bytes-aaaaaaaaa")
        cipher_b = TokenCipher(key="key-b-32-bytes-bbbbbbbbb")
        encrypted = cipher_a.encrypt("some-token")
        with pytest.raises(ValueError):
            cipher_b.decrypt(encrypted)

    def test_decrypt_garbage_raises_valueerror(self):
        cipher = TokenCipher(key="garbage-key-32-bytes!!!!")
        with pytest.raises(ValueError):
            cipher.decrypt("not-valid-ciphertext")

    def test_different_keys_produce_different_ciphertexts(self):
        """Same plaintext encrypted with different keys should differ."""
        a = TokenCipher(key="key-aaa-32-bytes-aaaaaaaaa")
        b = TokenCipher(key="key-bbb-32-bytes-bbbbbbbbb")
        plain = "same-token"
        assert a.encrypt(plain) != b.encrypt(plain)
