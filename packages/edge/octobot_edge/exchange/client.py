from __future__ import annotations

import hashlib
from base64 import b64encode

import ccxt
import ccxt.async_support as ccxt_async
from octobot_edge.crypto.hmac import maybe_rust_hmac


def create_exchange(
    exchange_id: str, config: dict, *, async_mode: bool = False
) -> ccxt.Exchange:
    """Return a ccxt exchange instance with optional Rust-backed signing."""
    cls = getattr(ccxt_async if async_mode else ccxt, exchange_id)
    instance = cls(config)
    _patch_signing(instance)
    return instance


def _normalize_algorithm(algorithm) -> str | None:
    """Convert algorithm argument (hashlib module or string) to a lowercase string."""
    if algorithm is None:
        return "sha256"
    if algorithm is hashlib.sha256:
        return "sha256"
    if algorithm is hashlib.sha512:
        return "sha512"
    if isinstance(algorithm, str):
        return algorithm.lower()
    return None


def _patch_signing(exchange: ccxt.Exchange) -> None:
    """Override ccxt hmac() with Rust implementation when available."""
    original = exchange.hmac

    def fast_hmac(request, secret, algorithm=None, digest="hex"):
        algo = _normalize_algorithm(algorithm)
        if algo in ("sha256", "sha512"):
            result = maybe_rust_hmac(
                secret.encode() if isinstance(secret, str) else secret,
                request.encode() if isinstance(request, str) else request,
                algorithm=algo,
            )
            if result is not None:
                if digest == "hex":
                    return result.hex()
                if digest == "base64":
                    return b64encode(result).decode("ascii")
                # For other digest formats (e.g. None -> raw bytes), return raw
                return result
        return original(request, secret, algorithm, digest)

    exchange.hmac = fast_hmac
