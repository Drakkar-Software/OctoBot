from __future__ import annotations

import hmac as _hmac
import hashlib

try:
    from octobot_edge._native import hmac_sha256 as _rust_hmac_sha256
    from octobot_edge._native import hmac_sha512 as _rust_hmac_sha512
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False


def maybe_rust_hmac(
    key: bytes, message: bytes, *, algorithm: str = "sha256"
) -> bytes | None:
    """Return HMAC bytes via Rust extension, or None if unavailable.

    Supports "sha256" and "sha512".
    """
    if _HAS_RUST:
        if algorithm == "sha256":
            return _rust_hmac_sha256(key, message)
        if algorithm == "sha512":
            return _rust_hmac_sha512(key, message)
    return None


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    """Always-available HMAC-SHA256 (stdlib fallback)."""
    if _HAS_RUST:
        return _rust_hmac_sha256(key, message)
    return _hmac.new(key, message, hashlib.sha256).digest()


def hmac_sha512(key: bytes, message: bytes) -> bytes:
    """Always-available HMAC-SHA512 (stdlib fallback)."""
    if _HAS_RUST:
        return _rust_hmac_sha512(key, message)
    return _hmac.new(key, message, hashlib.sha512).digest()
