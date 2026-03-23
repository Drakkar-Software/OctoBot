"""
End-to-end tests — verify the full flow from exchange creation through
signing to request assembly, matching ccxt's native behavior exactly.

Simple tests validate basic crypto and exchange creation.
Advanced tests exercise multi-exchange signing, concurrent usage,
binary/edge-case secrets, and cross-algorithm consistency.
"""
from __future__ import annotations

import hashlib
import hmac as stdlib_hmac
import secrets
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import ccxt

from octobot_edge import create_exchange, hmac_sha256, hmac_sha512, maybe_rust_hmac


# ═══════════════════════════════════════════════════════════════════════════
# Simple E2E Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSimpleE2E:
    """Simple end-to-end tests: create exchange, sign, verify."""

    def test_create_and_sign_binance(self):
        """Full flow: create Binance exchange, sign a request, verify output."""
        exchange = create_exchange("binance", {
            "apiKey": "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A",
            "secret": "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j",
        })

        query = b"symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
        secret = b"NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"

        result = exchange.hmac(query, secret, "sha256", "hex")
        expected = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"
        assert result == expected

    def test_create_and_sign_bybit(self):
        """Full flow: create Bybit exchange, sign a request."""
        exchange = create_exchange("bybit", {
            "apiKey": "test_api_key",
            "secret": "test_secret_key",
        })
        result = exchange.hmac(b"test_payload", b"test_secret_key", "sha256", "hex")
        expected = stdlib_hmac.new(b"test_secret_key", b"test_payload", hashlib.sha256).hexdigest()
        assert result == expected

    def test_direct_hmac_sha256_roundtrip(self):
        """Direct hmac_sha256 produces correct bytes that encode to hex properly."""
        key = b"my_secret"
        msg = b"timestamp=1700000000000"
        result = hmac_sha256(key, msg)
        expected = stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        assert result == expected
        assert result.hex() == expected.hex()

    def test_direct_hmac_sha512_roundtrip(self):
        """Direct hmac_sha512 produces correct bytes."""
        key = b"another_secret"
        msg = b"order_data"
        result = hmac_sha512(key, msg)
        expected = stdlib_hmac.new(key, msg, hashlib.sha512).digest()
        assert result == expected

    def test_exchange_methods_accessible(self):
        """Created exchange exposes all standard ccxt methods."""
        exchange = create_exchange("binance", {})
        for method in ["fetch_ticker", "fetch_order_book", "fetch_ohlcv",
                       "create_order", "cancel_order", "fetch_balance",
                       "fetch_trades", "fetch_markets"]:
            assert hasattr(exchange, method), f"Missing method: {method}"

    def test_maybe_rust_hmac_returns_bytes_or_none(self):
        """maybe_rust_hmac returns bytes for supported algos, None for unsupported."""
        key, msg = b"key", b"msg"
        sha256_result = maybe_rust_hmac(key, msg, algorithm="sha256")
        sha512_result = maybe_rust_hmac(key, msg, algorithm="sha512")
        unsupported = maybe_rust_hmac(key, msg, algorithm="md5")

        if sha256_result is not None:
            assert isinstance(sha256_result, bytes)
            assert sha256_result == stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        if sha512_result is not None:
            assert isinstance(sha512_result, bytes)
            assert sha512_result == stdlib_hmac.new(key, msg, hashlib.sha512).digest()
        assert unsupported is None


# ═══════════════════════════════════════════════════════════════════════════
# Advanced E2E Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAdvancedE2EMultiExchange:
    """Test signing across all major exchanges to verify patching is universal."""

    EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget", "kraken", "huobi", "gate"]
    TEST_PAYLOAD = b"symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
    TEST_SECRET = b"exchange_api_secret_key_12345"

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_each_exchange_hmac_matches_stdlib(self, exchange_id):
        """Every supported exchange's patched HMAC must match Python stdlib."""
        try:
            exchange = create_exchange(exchange_id, {"apiKey": "k", "secret": "s"})
        except Exception:
            pytest.skip(f"{exchange_id} not available in this ccxt version")

        for algo, hashfn in [("sha256", hashlib.sha256), ("sha512", hashlib.sha512)]:
            patched = exchange.hmac(self.TEST_PAYLOAD, self.TEST_SECRET, algo, "hex")
            expected = stdlib_hmac.new(self.TEST_SECRET, self.TEST_PAYLOAD, hashfn).hexdigest()
            assert patched == expected, f"{exchange_id}/{algo}: {patched} != {expected}"

    def test_cross_exchange_signatures_are_identical(self):
        """All exchanges with the same input must produce the same signature."""
        results = {}
        for eid in self.EXCHANGES:
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                results[eid] = ex.hmac(self.TEST_PAYLOAD, self.TEST_SECRET, "sha256", "hex")
            except Exception:
                pass

        values = list(results.values())
        assert len(values) >= 2, "Need at least 2 exchanges to compare"
        assert len(set(values)) == 1, f"Signatures differ across exchanges: {results}"


class TestAdvancedE2EConcurrency:
    """Test signing under concurrent access to verify thread safety."""

    def test_concurrent_signing_is_thread_safe(self):
        """Multiple threads signing simultaneously should all produce correct results."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"concurrent_test_secret"
        errors = []

        def sign_and_verify(thread_id: int):
            for i in range(100):
                msg = f"thread={thread_id}&iter={i}&timestamp=1700000000000".encode()
                result = exchange.hmac(msg, secret, "sha256", "hex")
                expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
                if result != expected:
                    errors.append(f"Thread {thread_id}, iter {i}: {result} != {expected}")

        threads = [threading.Thread(target=sign_and_verify, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors:\n" + "\n".join(errors[:10])

    def test_concurrent_exchange_creation(self):
        """Creating and using exchanges concurrently should be safe."""
        results = {}

        def create_and_sign(exchange_id: str):
            ex = create_exchange(exchange_id, {"apiKey": "k", "secret": "s"})
            sig = ex.hmac(b"test_data", b"test_secret", "sha256", "hex")
            return exchange_id, sig

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(create_and_sign, eid) for eid in ["binance", "bybit", "okx", "kucoin"]]
            for f in as_completed(futures):
                eid, sig = f.result()
                results[eid] = sig

        expected = stdlib_hmac.new(b"test_secret", b"test_data", hashlib.sha256).hexdigest()
        for eid, sig in results.items():
            assert sig == expected, f"{eid} concurrent result mismatch"


class TestAdvancedE2EBinarySecrets:
    """Test signing with various binary secret formats (base64-decoded, raw bytes)."""

    def test_base64_decoded_secret(self):
        """Exchanges like Coinbase use base64-encoded secrets."""
        import base64
        raw_secret = secrets.token_bytes(32)
        b64_secret = base64.b64encode(raw_secret)

        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(b"test", raw_secret, "sha256", "hex")
        expected = stdlib_hmac.new(raw_secret, b"test", hashlib.sha256).hexdigest()
        assert result == expected

    def test_secret_with_all_byte_values(self):
        """Secret containing every possible byte value (0x00–0xFF)."""
        secret = bytes(range(256))
        message = b"sign_this"

        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(message, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, message, hashlib.sha256).hexdigest()
        assert result == expected

    def test_empty_inputs(self):
        """Empty message and/or empty secret should still produce valid HMAC."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})

        for msg, secret in [(b"", b"key"), (b"msg", b""), (b"", b"")]:
            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected, f"Empty input mismatch: msg={msg!r}, secret={secret!r}"

    def test_very_large_payload(self):
        """Large payloads (1MB) should sign correctly without truncation."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"x" * (1024 * 1024)
        secret = b"secret"

        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_unicode_query_string(self):
        """Non-ASCII characters in query strings."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = "symbol=BTC/USDT&note=日本語テスト&price=1000€".encode("utf-8")
        secret = b"secret"

        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected


class TestAdvancedE2EAlgorithmConsistency:
    """Verify cross-algorithm consistency and fallback behavior."""

    def test_sha256_and_sha512_differ(self):
        """Same input with different algorithms must produce different signatures."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg, secret = b"test", b"secret"

        sha256 = exchange.hmac(msg, secret, "sha256", "hex")
        sha512 = exchange.hmac(msg, secret, "sha512", "hex")

        assert sha256 != sha512
        assert len(sha256) == 64   # SHA-256 = 32 bytes = 64 hex chars
        assert len(sha512) == 128  # SHA-512 = 64 bytes = 128 hex chars

    def test_direct_and_exchange_hmac_agree(self):
        """Direct hmac_sha256/sha512 and exchange.hmac produce identical results."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg, secret = b"payload_data", b"api_secret"

        direct_256 = hmac_sha256(secret, msg).hex()
        exchange_256 = exchange.hmac(msg, secret, "sha256", "hex")
        assert direct_256 == exchange_256

        direct_512 = hmac_sha512(secret, msg).hex()
        exchange_512 = exchange.hmac(msg, secret, "sha512", "hex")
        assert direct_512 == exchange_512

    def test_sync_and_async_exchange_agree(self):
        """Sync and async exchanges must produce identical signatures."""
        sync_ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        async_ex = create_exchange("binance", {"apiKey": "k", "secret": "s"}, async_mode=True)

        msg, secret = b"timestamp=1700000000000", b"secret"
        assert sync_ex.hmac(msg, secret, "sha256", "hex") == async_ex.hmac(msg, secret, "sha256", "hex")
        assert sync_ex.hmac(msg, secret, "sha512", "hex") == async_ex.hmac(msg, secret, "sha512", "hex")

    def test_many_random_inputs(self):
        """Fuzz: 500 random payloads must all match stdlib."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})

        for _ in range(500):
            msg = secrets.token_bytes(secrets.randbelow(512) + 1)
            secret = secrets.token_bytes(secrets.randbelow(128) + 1)

            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected


class TestAdvancedE2ESigningFlow:
    """Test the full request-signing flow as exchanges do it internally."""

    def test_binance_order_signing_flow(self):
        """Simulate the full Binance order signing flow."""
        api_key = "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
        api_secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"

        exchange = create_exchange("binance", {
            "apiKey": api_key,
            "secret": api_secret,
        })

        # Build query string as Binance SDK does
        params = {
            "symbol": "LTCBTC",
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": "1",
            "price": "0.1",
            "recvWindow": "5000",
            "timestamp": "1499827319559",
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        signature = exchange.hmac(
            query_string.encode(), api_secret.encode(), "sha256", "hex"
        )

        # Verify against Binance's documented expected signature
        assert signature == "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"

        # The signed URL would be: query_string + &signature=<signature>
        signed_url = f"{query_string}&signature={signature}"
        assert "signature=c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71" in signed_url

    def test_rapid_successive_different_signatures(self):
        """Rapidly signing different messages should never cross-contaminate."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"secret"

        prev = None
        for i in range(1000):
            msg = f"nonce={i}".encode()
            sig = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert sig == expected
            assert sig != prev, f"Signatures should differ: iter {i}"
            prev = sig
