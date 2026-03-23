"""Tests for octobot_edge.crypto — verifies HMAC correctness with known vectors."""
import hashlib
import hmac as stdlib_hmac

import pytest

from octobot_edge.crypto.hmac import hmac_sha256, hmac_sha512, maybe_rust_hmac


class TestHmacSha256:
    """Test HMAC-SHA256 against known vectors and stdlib."""

    BINANCE_SECRET = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    BINANCE_QUERY = (
        "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC"
        "&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
    )
    BINANCE_EXPECTED = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"

    def test_binance_signature_vector(self):
        """Verify HMAC-SHA256 against the official Binance API docs test vector."""
        result = hmac_sha256(
            self.BINANCE_SECRET.encode(),
            self.BINANCE_QUERY.encode(),
        )
        assert result.hex() == self.BINANCE_EXPECTED

    def test_matches_stdlib(self):
        """Verify our HMAC matches Python stdlib for arbitrary inputs."""
        key = b"test-secret-key"
        msg = b"test-message-data"
        expected = stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        assert hmac_sha256(key, msg) == expected

    def test_empty_message(self):
        """HMAC of empty message should still produce 32-byte output."""
        result = hmac_sha256(b"key", b"")
        assert len(result) == 32

    def test_empty_key(self):
        """HMAC with empty key should still produce valid output."""
        result = hmac_sha256(b"", b"message")
        expected = stdlib_hmac.new(b"", b"message", hashlib.sha256).digest()
        assert result == expected

    def test_binary_key(self):
        """HMAC with binary key (non-UTF-8 bytes)."""
        key = bytes(range(256))
        msg = b"binary key test"
        expected = stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        assert hmac_sha256(key, msg) == expected


class TestHmacSha512:
    """Test HMAC-SHA512 against known vectors and stdlib."""

    def test_matches_stdlib(self):
        """Verify our HMAC-SHA512 matches Python stdlib."""
        key = b"test-secret-key"
        msg = b"test-message-data"
        expected = stdlib_hmac.new(key, msg, hashlib.sha512).digest()
        assert hmac_sha512(key, msg) == expected

    def test_output_length(self):
        """HMAC-SHA512 should produce 64 bytes."""
        result = hmac_sha512(b"key", b"message")
        assert len(result) == 64

    def test_empty_message(self):
        """HMAC-SHA512 of empty message should still produce 64-byte output."""
        result = hmac_sha512(b"key", b"")
        expected = stdlib_hmac.new(b"key", b"", hashlib.sha512).digest()
        assert result == expected

    def test_empty_key(self):
        """HMAC-SHA512 with empty key matches stdlib."""
        result = hmac_sha512(b"", b"message")
        expected = stdlib_hmac.new(b"", b"message", hashlib.sha512).digest()
        assert result == expected


class TestMaybeRustHmac:
    """Test the maybe_rust_hmac fallback logic."""

    def test_returns_bytes_or_none_sha256(self):
        """Should return bytes (Rust available) or None (fallback)."""
        result = maybe_rust_hmac(b"key", b"message")
        if result is not None:
            assert isinstance(result, bytes)
            assert len(result) == 32

    def test_returns_bytes_or_none_sha512(self):
        """SHA-512 variant should return 64 bytes or None."""
        result = maybe_rust_hmac(b"key", b"message", algorithm="sha512")
        if result is not None:
            assert isinstance(result, bytes)
            assert len(result) == 64
            expected = stdlib_hmac.new(b"key", b"message", hashlib.sha512).digest()
            assert result == expected

    def test_unsupported_algorithm_returns_none(self):
        """Unsupported algorithm should return None (no Rust dispatch)."""
        result = maybe_rust_hmac(b"key", b"message", algorithm="sha384")
        assert result is None
