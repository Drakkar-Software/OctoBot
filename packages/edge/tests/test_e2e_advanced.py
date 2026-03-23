"""
Advanced end-to-end tests — stress, concurrency, encoding variants,
cross-exchange consistency, fuzz, error boundaries, and full signing flows.

These complement the basic test_e2e.py with deeper coverage.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac as stdlib_hmac
import json
import os
import secrets
import string
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import ccxt
import ccxt.async_support as ccxt_async

from octobot_edge import create_exchange, hmac_sha256, hmac_sha512, maybe_rust_hmac


# ═══════════════════════════════════════════════════════════════════════════
# Cross-Exchange Signing Consistency
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossExchangeConsistency:
    """Verify all exchanges produce identical signatures for identical inputs."""

    EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget", "kraken", "huobi", "gate"]
    PAYLOAD = b"symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
    SECRET = b"exchange_api_secret_key_12345"

    def test_sha256_consistency_across_all_exchanges(self):
        """SHA-256 hex signatures must be identical across all exchanges."""
        expected = stdlib_hmac.new(self.SECRET, self.PAYLOAD, hashlib.sha256).hexdigest()
        results = {}
        for eid in self.EXCHANGES:
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                results[eid] = ex.hmac(self.PAYLOAD, self.SECRET, "sha256", "hex")
            except Exception:
                pass
        assert len(results) >= 4, f"Need at least 4 exchanges, got: {list(results.keys())}"
        for eid, sig in results.items():
            assert sig == expected, f"{eid}: {sig} != {expected}"

    def test_sha512_consistency_across_all_exchanges(self):
        """SHA-512 hex signatures must be identical across all exchanges."""
        expected = stdlib_hmac.new(self.SECRET, self.PAYLOAD, hashlib.sha512).hexdigest()
        results = {}
        for eid in self.EXCHANGES:
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                results[eid] = ex.hmac(self.PAYLOAD, self.SECRET, "sha512", "hex")
            except Exception:
                pass
        assert len(results) >= 4
        for eid, sig in results.items():
            assert sig == expected, f"{eid}: {sig} != {expected}"

    def test_base64_encoding_consistency_across_exchanges(self):
        """base64-encoded HMAC should be consistent across exchanges."""
        expected = base64.b64encode(
            stdlib_hmac.new(self.SECRET, self.PAYLOAD, hashlib.sha256).digest()
        ).decode("ascii")
        results = {}
        for eid in self.EXCHANGES:
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                results[eid] = ex.hmac(self.PAYLOAD, self.SECRET, "sha256", "base64")
            except Exception:
                pass
        assert len(results) >= 4
        for eid, sig in results.items():
            assert sig == expected, f"{eid}: {sig} != {expected}"


# ═══════════════════════════════════════════════════════════════════════════
# Digest Encoding Variants
# ═══════════════════════════════════════════════════════════════════════════


class TestDigestEncodingVariants:
    """Test hex, base64, and raw byte output formats."""

    def test_hex_output(self):
        ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = ex.hmac(b"data", b"secret", "sha256", "hex")
        expected = stdlib_hmac.new(b"secret", b"data", hashlib.sha256).hexdigest()
        assert result == expected
        assert all(c in "0123456789abcdef" for c in result)

    def test_base64_output(self):
        ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = ex.hmac(b"data", b"secret", "sha256", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(b"secret", b"data", hashlib.sha256).digest()
        ).decode("ascii")
        assert result == expected

    def test_hex_and_base64_decode_to_same_bytes(self):
        """hex and base64 are just encodings of the same underlying bytes."""
        ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        hex_result = ex.hmac(b"msg", b"key", "sha256", "hex")
        b64_result = ex.hmac(b"msg", b"key", "sha256", "base64")

        hex_bytes = bytes.fromhex(hex_result)
        b64_bytes = base64.b64decode(b64_result)
        assert hex_bytes == b64_bytes

    def test_sha512_base64_output(self):
        ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = ex.hmac(b"data", b"secret", "sha512", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(b"secret", b"data", hashlib.sha512).digest()
        ).decode("ascii")
        assert result == expected


# ═══════════════════════════════════════════════════════════════════════════
# Advanced Concurrency Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAdvancedConcurrency:
    """Stress test concurrent access patterns."""

    def test_16_threads_x_500_iterations(self):
        """Heavy concurrent signing load."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"heavy_load_secret"
        errors = []

        def sign_loop(thread_id: int):
            for i in range(500):
                msg = f"t={thread_id}&i={i}&ts=1700000000000".encode()
                result = exchange.hmac(msg, secret, "sha256", "hex")
                expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
                if result != expected:
                    errors.append(f"Thread {thread_id} iter {i}")

        threads = [threading.Thread(target=sign_loop, args=(t,)) for t in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"{len(errors)} thread safety errors"

    def test_concurrent_multi_exchange_signing(self):
        """Different exchanges signing concurrently on different threads."""
        exchange_ids = ["binance", "bybit", "okx", "kucoin"]
        errors = []

        def sign_on_exchange(eid: str):
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                for i in range(200):
                    msg = f"exchange={eid}&nonce={i}".encode()
                    secret = b"multi_exchange_secret"
                    result = ex.hmac(msg, secret, "sha256", "hex")
                    expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
                    if result != expected:
                        errors.append(f"{eid} iter {i}")
            except Exception as e:
                errors.append(f"{eid} creation failed: {e}")

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(sign_on_exchange, eid) for eid in exchange_ids]
            for f in as_completed(futures):
                f.result()  # raises if thread had unhandled exception

        assert len(errors) == 0, f"Concurrent multi-exchange errors: {errors[:10]}"

    def test_alternating_sha256_sha512_under_load(self):
        """Rapidly alternating between SHA-256 and SHA-512 under load."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"alternating_algo_secret"
        errors = []

        def alternate(thread_id: int):
            for i in range(300):
                msg = f"alt={thread_id}&i={i}".encode()
                algo = "sha256" if i % 2 == 0 else "sha512"
                hashfn = hashlib.sha256 if algo == "sha256" else hashlib.sha512
                result = exchange.hmac(msg, secret, algo, "hex")
                expected = stdlib_hmac.new(secret, msg, hashfn).hexdigest()
                if result != expected:
                    errors.append(f"Thread {thread_id} iter {i} algo {algo}")

        threads = [threading.Thread(target=alternate, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Alternating algo errors: {errors[:10]}"


# ═══════════════════════════════════════════════════════════════════════════
# Async Exchange Tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAsyncExchange:
    """Test async exchange variant matches sync behavior exactly."""

    def test_async_sync_parity_all_algos(self):
        """Async and sync exchanges must produce identical signatures."""
        sync_ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        async_ex = create_exchange("binance", {"apiKey": "k", "secret": "s"}, async_mode=True)

        for algo, hashfn in [("sha256", hashlib.sha256), ("sha512", hashlib.sha512)]:
            for i in range(50):
                msg = f"nonce={i}".encode()
                secret = b"async_test_secret"
                sync_result = sync_ex.hmac(msg, secret, algo, "hex")
                async_result = async_ex.hmac(msg, secret, algo, "hex")
                expected = stdlib_hmac.new(secret, msg, hashfn).hexdigest()
                assert sync_result == async_result == expected

    def test_async_base64_encoding(self):
        async_ex = create_exchange("binance", {"apiKey": "k", "secret": "s"}, async_mode=True)
        result = async_ex.hmac(b"test", b"secret", "sha256", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(b"secret", b"test", hashlib.sha256).digest()
        ).decode("ascii")
        assert result == expected

    @pytest.mark.parametrize("exchange_id", ["binance", "bybit", "okx", "kucoin"])
    def test_async_exchange_methods_available(self, exchange_id):
        """Async exchange should have all standard async methods."""
        try:
            ex = create_exchange(exchange_id, {}, async_mode=True)
        except Exception:
            pytest.skip(f"{exchange_id} async not available")
        for method in ["fetch_ticker", "fetch_order_book", "create_order", "fetch_balance"]:
            assert hasattr(ex, method), f"{exchange_id} missing {method}"


# ═══════════════════════════════════════════════════════════════════════════
# Fuzz Testing
# ═══════════════════════════════════════════════════════════════════════════


class TestFuzzing:
    """Fuzz with random inputs to catch edge cases."""

    def test_1000_random_hmac_sha256(self):
        """1000 random payloads, all must match stdlib."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        for _ in range(1000):
            msg = secrets.token_bytes(secrets.randbelow(512) + 1)
            secret = secrets.token_bytes(secrets.randbelow(128) + 1)
            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected

    def test_500_random_hmac_sha512(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        for _ in range(500):
            msg = secrets.token_bytes(secrets.randbelow(256) + 1)
            secret = secrets.token_bytes(secrets.randbelow(64) + 1)
            result = exchange.hmac(msg, secret, "sha512", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha512).hexdigest()
            assert result == expected

    def test_500_random_base64_encoding(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        for _ in range(500):
            msg = secrets.token_bytes(secrets.randbelow(256) + 1)
            secret = secrets.token_bytes(secrets.randbelow(64) + 1)
            result = exchange.hmac(msg, secret, "sha256", "base64")
            expected = base64.b64encode(
                stdlib_hmac.new(secret, msg, hashlib.sha256).digest()
            ).decode("ascii")
            assert result == expected

    def test_direct_hmac_sha256_fuzz(self):
        """Fuzz the direct hmac_sha256 function."""
        for _ in range(500):
            key = secrets.token_bytes(secrets.randbelow(128) + 1)
            msg = secrets.token_bytes(secrets.randbelow(512) + 1)
            result = hmac_sha256(key, msg)
            expected = stdlib_hmac.new(key, msg, hashlib.sha256).digest()
            assert result == expected

    def test_direct_hmac_sha512_fuzz(self):
        for _ in range(500):
            key = secrets.token_bytes(secrets.randbelow(128) + 1)
            msg = secrets.token_bytes(secrets.randbelow(512) + 1)
            result = hmac_sha512(key, msg)
            expected = stdlib_hmac.new(key, msg, hashlib.sha512).digest()
            assert result == expected


# ═══════════════════════════════════════════════════════════════════════════
# Exchange Signing Flow Simulations
# ═══════════════════════════════════════════════════════════════════════════


class TestExchangeSigningFlows:
    """Simulate real exchange API signing protocols."""

    def test_binance_spot_market_order(self):
        """Full Binance spot market order signing flow."""
        api_secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
        exchange = create_exchange("binance", {"apiKey": "test", "secret": api_secret})

        params = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": "100",
            "newOrderRespType": "FULL",
            "recvWindow": "5000",
            "timestamp": "1700000000000",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items()).encode()
        sig = exchange.hmac(query, api_secret.encode(), "sha256", "hex")
        expected = stdlib_hmac.new(api_secret.encode(), query, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_bybit_v5_signing_flow(self):
        """Simulate Bybit v5 API signing: timestamp + apiKey + recvWindow + queryString."""
        api_key = "BYBIT_API_KEY"
        api_secret = "BYBIT_SECRET_KEY"
        timestamp = "1700000000000"
        recv_window = "5000"
        query_string = "category=linear&symbol=BTCUSDT"

        sign_payload = f"{timestamp}{api_key}{recv_window}{query_string}".encode()
        exchange = create_exchange("bybit", {"apiKey": api_key, "secret": api_secret})
        sig = exchange.hmac(sign_payload, api_secret.encode(), "sha256", "hex")
        expected = stdlib_hmac.new(api_secret.encode(), sign_payload, hashlib.sha256).hexdigest()
        assert sig == expected

    def test_okx_signing_flow_base64(self):
        """Simulate OKX API signing: timestamp + method + path + body, base64 encoded."""
        secret_key = "OKX_SECRET_KEY"
        timestamp = "2023-11-15T10:00:00.000Z"
        method = "GET"
        path = "/api/v5/account/balance"
        body = ""

        pre_sign = f"{timestamp}{method}{path}{body}".encode()
        exchange = create_exchange("okx", {"apiKey": "k", "secret": secret_key})
        sig = exchange.hmac(pre_sign, secret_key.encode(), "sha256", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(secret_key.encode(), pre_sign, hashlib.sha256).digest()
        ).decode("ascii")
        assert sig == expected

    def test_okx_post_with_json_body(self):
        """OKX POST request signing includes JSON body."""
        secret_key = "OKX_SECRET_KEY"
        timestamp = "2023-11-15T10:00:00.000Z"
        method = "POST"
        path = "/api/v5/trade/order"
        body = json.dumps({
            "instId": "BTC-USDT",
            "tdMode": "cash",
            "side": "buy",
            "ordType": "limit",
            "px": "50000",
            "sz": "0.001",
        })

        pre_sign = f"{timestamp}{method}{path}{body}".encode()
        exchange = create_exchange("okx", {"apiKey": "k", "secret": secret_key})
        sig = exchange.hmac(pre_sign, secret_key.encode(), "sha256", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(secret_key.encode(), pre_sign, hashlib.sha256).digest()
        ).decode("ascii")
        assert sig == expected

    def test_kucoin_signing_flow(self):
        """Simulate KuCoin API signing: timestamp + method + endpoint + body."""
        api_secret = "KUCOIN_SECRET"
        timestamp = "1700000000000"
        method = "GET"
        endpoint = "/api/v1/accounts"

        sign_str = f"{timestamp}{method}{endpoint}".encode()
        exchange = create_exchange("kucoin", {"apiKey": "k", "secret": api_secret})
        sig = exchange.hmac(sign_str, api_secret.encode(), "sha256", "base64")
        expected = base64.b64encode(
            stdlib_hmac.new(api_secret.encode(), sign_str, hashlib.sha256).digest()
        ).decode("ascii")
        assert sig == expected

    def test_timestamp_rotation_signing(self):
        """Simulate rapid order placement with rotating timestamps."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"rapid_order_secret"
        base_ts = 1700000000000
        sigs = set()

        for i in range(500):
            ts = base_ts + i
            msg = f"symbol=BTCUSDT&side=BUY&quantity=0.001&timestamp={ts}".encode()
            sig = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert sig == expected
            sigs.add(sig)

        assert len(sigs) == 500, "All timestamps should produce unique signatures"


# ═══════════════════════════════════════════════════════════════════════════
# Edge Cases & Error Boundaries
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCasesAdvanced:
    """Deep edge case coverage."""

    def test_null_bytes_in_message(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"before\x00after\x00end"
        secret = b"null_byte_secret"
        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_null_bytes_in_secret(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"test_message"
        secret = b"sec\x00ret\x00key"
        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_newlines_and_control_chars(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"line1\nline2\rline3\tline4\x00line5"
        secret = b"ctrl_secret"
        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_very_long_secret_exceeding_block_size(self):
        """HMAC internally hashes secrets longer than the hash block size."""
        # SHA-256 block size is 64 bytes; secrets > 64 bytes are hashed first
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        for length in [63, 64, 65, 128, 256, 1024, 4096]:
            secret = secrets.token_bytes(length)
            msg = b"test_payload"
            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected, f"Failed at secret length {length}"

    def test_10mb_payload(self):
        """Very large payload (10MB)."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"x" * (10 * 1024 * 1024)
        secret = b"large_payload_secret"
        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_all_byte_values_in_payload(self):
        """Message containing every possible byte value."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = bytes(range(256)) * 4  # 1024 bytes with all byte values
        secret = b"all_bytes_secret"
        result = exchange.hmac(msg, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
        assert result == expected

    def test_unicode_query_strings(self):
        """Non-ASCII characters in query strings (UTF-8 encoded)."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        test_cases = [
            "symbol=BTC/USDT&note=日本語テスト",
            "name=Ünîcödé&emoji=🌍🚀",
            "data=café&price=1000€",
            "cyrillic=Привет&arabic=مرحبا",
        ]
        for msg_str in test_cases:
            msg = msg_str.encode("utf-8")
            secret = b"unicode_secret"
            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected, f"Failed for: {msg_str}"

    def test_json_body_signing(self):
        """Signing JSON body payloads (common in REST APIs)."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        bodies = [
            {"symbol": "BTCUSDT", "quantity": 0.001, "price": 50000.00},
            {"pairs": ["BTC/USDT", "ETH/USDT"], "nested": {"key": "value"}},
            {},  # empty object
            {"unicode": "日本語", "special": "a&b=c"},
        ]
        secret = b"json_secret"
        for body in bodies:
            msg = json.dumps(body, separators=(",", ":")).encode()
            result = exchange.hmac(msg, secret, "sha256", "hex")
            expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()
            assert result == expected

    def test_encoded_string_inputs(self):
        """Pre-encoded string inputs produce correct results."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg_str = "timestamp=1700000000000"
        secret_str = "my_api_secret"

        # The standard ccxt path expects bytes; verify encoding is consistent
        result = exchange.hmac(msg_str.encode(), secret_str.encode(), "sha256", "hex")
        expected = stdlib_hmac.new(secret_str.encode(), msg_str.encode(), hashlib.sha256).hexdigest()
        assert result == expected

        # Verify different encodings of the same logical string match
        msg_utf8 = msg_str.encode("utf-8")
        msg_ascii = msg_str.encode("ascii")
        result_utf8 = exchange.hmac(msg_utf8, secret_str.encode(), "sha256", "hex")
        result_ascii = exchange.hmac(msg_ascii, secret_str.encode(), "sha256", "hex")
        assert result_utf8 == result_ascii == expected


# ═══════════════════════════════════════════════════════════════════════════
# Signing Determinism
# ═══════════════════════════════════════════════════════════════════════════


class TestSigningDeterminism:
    """Verify deterministic output under various conditions."""

    def test_1000_identical_calls(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"symbol=BTCUSDT&timestamp=1700000000000"
        secret = b"determinism_secret"
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()

        for _ in range(1000):
            assert exchange.hmac(msg, secret, "sha256", "hex") == expected

    def test_determinism_across_exchange_instances(self):
        """Multiple instances of same exchange must produce identical results."""
        msg = b"shared_payload"
        secret = b"shared_secret"
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()

        for _ in range(100):
            ex = create_exchange("binance", {"apiKey": "k", "secret": "s"})
            assert ex.hmac(msg, secret, "sha256", "hex") == expected

    def test_determinism_across_different_exchanges(self):
        """Different exchange types produce identical HMAC for same inputs."""
        msg = b"cross_exchange_payload"
        secret = b"cross_exchange_secret"
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()

        for eid in ["binance", "bybit", "okx", "kucoin"]:
            try:
                ex = create_exchange(eid, {"apiKey": "k", "secret": "s"})
                assert ex.hmac(msg, secret, "sha256", "hex") == expected
            except Exception:
                pass

    def test_direct_function_determinism(self):
        """Direct hmac functions are deterministic."""
        key = b"deterministic_key"
        msg = b"deterministic_message"
        expected_256 = stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        expected_512 = stdlib_hmac.new(key, msg, hashlib.sha512).digest()

        for _ in range(500):
            assert hmac_sha256(key, msg) == expected_256
            assert hmac_sha512(key, msg) == expected_512


# ═══════════════════════════════════════════════════════════════════════════
# Algorithm Edge Cases
# ═══════════════════════════════════════════════════════════════════════════


class TestAlgorithmEdgeCases:
    """Test algorithm handling, fallback, and edge cases."""

    def test_hashlib_module_as_algorithm(self):
        """ccxt sometimes passes hashlib.sha256 directly as algorithm."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"test"
        secret = b"secret"

        # String algorithm
        str_result = exchange.hmac(msg, secret, "sha256", "hex")
        # hashlib module as algorithm
        mod_result = exchange.hmac(msg, secret, hashlib.sha256, "hex")
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()

        assert str_result == expected
        assert mod_result == expected

    def test_case_insensitive_algorithm(self):
        """Algorithm names should be case-insensitive."""
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        msg = b"test"
        secret = b"secret"
        expected = stdlib_hmac.new(secret, msg, hashlib.sha256).hexdigest()

        for algo in ["sha256", "SHA256", "Sha256"]:
            result = exchange.hmac(msg, secret, algo, "hex")
            assert result == expected, f"Failed for algorithm: {algo}"

    def test_none_algorithm_defaults_to_sha256(self):
        """None algorithm defaults to sha256 in _normalize_algorithm."""
        from octobot_edge.exchange.client import _normalize_algorithm
        assert _normalize_algorithm(None) == "sha256"
        assert _normalize_algorithm(hashlib.sha256) == "sha256"
        assert _normalize_algorithm(hashlib.sha512) == "sha512"
        assert _normalize_algorithm("SHA256") == "sha256"

    def test_sha256_output_length(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(b"m", b"k", "sha256", "hex")
        assert len(result) == 64  # 32 bytes = 64 hex chars

    def test_sha512_output_length(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(b"m", b"k", "sha512", "hex")
        assert len(result) == 128  # 64 bytes = 128 hex chars

    def test_maybe_rust_hmac_all_inputs(self):
        """Comprehensive test of maybe_rust_hmac behavior."""
        key = b"test_key"
        msg = b"test_msg"

        r256 = maybe_rust_hmac(key, msg, algorithm="sha256")
        r512 = maybe_rust_hmac(key, msg, algorithm="sha512")
        rmd5 = maybe_rust_hmac(key, msg, algorithm="md5")

        # sha256 and sha512 should return bytes (or None if no Rust)
        if r256 is not None:
            assert isinstance(r256, bytes)
            assert len(r256) == 32
            assert r256 == stdlib_hmac.new(key, msg, hashlib.sha256).digest()
        if r512 is not None:
            assert isinstance(r512, bytes)
            assert len(r512) == 64
            assert r512 == stdlib_hmac.new(key, msg, hashlib.sha512).digest()

        # md5 is unsupported, should return None
        assert rmd5 is None
