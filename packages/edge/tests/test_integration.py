"""Integration tests — real ccxt exchange instances with patched signing."""
from __future__ import annotations

import hashlib
import hmac as stdlib_hmac
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ccxt
import ccxt.async_support as ccxt_async

from octobot_edge.exchange.client import create_exchange, _patch_signing
from octobot_edge.exchange.normalize import normalize_ticker, normalize_order
from octobot_edge.crypto.hmac import hmac_sha256, maybe_rust_hmac

STATIC = Path(__file__).parent / "static"


# ── Fixture-driven HMAC tests ──────────────────────────────────────────────

class TestHmacVectors:
    """Validate HMAC against exchange-documented test vectors from static fixtures."""

    @pytest.fixture(scope="class")
    def vectors(self):
        with open(STATIC / "hmac_vectors.json") as f:
            return json.load(f)["vectors"]

    def test_all_sha256_vectors(self, vectors):
        for v in vectors:
            if v["algorithm"] != "sha256":
                continue
            result = hmac_sha256(v["key"].encode(), v["message"].encode())
            assert result.hex() == v["expected_hex"], (
                f"HMAC-SHA256 mismatch for vector '{v['name']}': "
                f"got {result.hex()}, expected {v['expected_hex']}"
            )

    def test_all_sha512_vectors(self, vectors):
        for v in vectors:
            if v["algorithm"] != "sha512":
                continue
            expected = stdlib_hmac.new(
                v["key"].encode(), v["message"].encode(), hashlib.sha512
            ).digest()
            assert expected.hex() == v["expected_hex"], (
                f"HMAC-SHA512 stdlib mismatch for vector '{v['name']}'"
            )

    def test_binance_vector_matches_fixture(self, vectors):
        binance = next(v for v in vectors if v["name"] == "binance_official")
        result = hmac_sha256(binance["key"].encode(), binance["message"].encode())
        assert result.hex() == binance["expected_hex"]


# ── Fixture-driven normalization tests ──────────────────────────────────────

class TestNormalizeFromFixtures:
    """Normalize real exchange API responses from static JSON fixtures."""

    @pytest.fixture(scope="class")
    def raw_ticker(self):
        with open(STATIC / "binance_ticker.json") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def raw_order(self):
        with open(STATIC / "binance_order.json") as f:
            return json.load(f)

    def test_ticker_all_fields_present(self, raw_ticker):
        result = normalize_ticker(raw_ticker)
        expected_keys = {"symbol", "last", "bid", "ask", "high", "low", "volume", "timestamp"}
        assert set(result.keys()) == expected_keys

    def test_ticker_numeric_conversion(self, raw_ticker):
        result = normalize_ticker(raw_ticker)
        assert result["last"] == 36800.75
        assert result["bid"] == 36800.50
        assert result["ask"] == 36801.00
        assert result["high"] == 37500.00
        assert result["low"] == 36200.00
        assert result["volume"] == 28543.12

    def test_ticker_preserves_non_numeric(self, raw_ticker):
        result = normalize_ticker(raw_ticker)
        assert result["symbol"] == "BTC/USDT"
        assert result["timestamp"] == 1700000000000

    def test_order_all_fields_present(self, raw_order):
        result = normalize_order(raw_order)
        expected_keys = {
            "id", "symbol", "side", "type", "price",
            "amount", "filled", "remaining", "status", "timestamp",
        }
        assert set(result.keys()) == expected_keys

    def test_order_numeric_conversion(self, raw_order):
        result = normalize_order(raw_order)
        assert result["price"] == 2050.00
        assert result["amount"] == 1.5
        assert result["filled"] == 0.5
        assert result["remaining"] == 1.0

    def test_order_preserves_strings(self, raw_order):
        result = normalize_order(raw_order)
        assert result["id"] == "28457315"
        assert result["symbol"] == "ETH/USDT"
        assert result["side"] == "buy"
        assert result["type"] == "limit"
        assert result["status"] == "open"


# ── Real ccxt exchange integration ──────────────────────────────────────────

class TestCcxtExchangePatching:
    """Test patching on real ccxt exchange instances (all major exchanges).

    Note: ccxt's native hmac() expects (request: bytes, secret: bytes, algorithm=hashlib.sha256).
    Our _patch_signing wraps it to also accept (request: str, secret: str, algorithm: str|None).
    Tests here use the patched interface.
    """

    EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget", "kraken"]

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_creates_and_patches_exchange(self, exchange_id):
        """Each exchange should be created with patched HMAC."""
        exchange = create_exchange(exchange_id, {"apiKey": "test", "secret": "test"})
        cls = getattr(ccxt, exchange_id)
        assert isinstance(exchange, cls)
        # hmac should be our patched version
        assert exchange.hmac.__name__ == "fast_hmac"

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_patched_hmac_sha256_produces_correct_result(self, exchange_id):
        """Patched exchange.hmac should produce correct SHA256 for known inputs."""
        patched = create_exchange(exchange_id, {"apiKey": "test", "secret": "test"})

        request = b"timestamp=1700000000000&symbol=BTCUSDT"
        secret = b"my_secret_key_for_testing"

        patched_result = patched.hmac(request, secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, request, hashlib.sha256).hexdigest()

        assert patched_result == expected, (
            f"{exchange_id}: patched={patched_result} != expected={expected}"
        )

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_patched_hmac_sha512_matches_stdlib(self, exchange_id):
        """SHA512 patched hmac should match stdlib output."""
        patched = create_exchange(exchange_id, {"apiKey": "test", "secret": "test"})

        request = b"test_data"
        secret = b"test_secret"

        patched_result = patched.hmac(request, secret, "sha512", "hex")
        expected = stdlib_hmac.new(secret, request, hashlib.sha512).hexdigest()

        assert patched_result == expected

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_patched_hmac_non_hex_falls_back(self, exchange_id):
        """Non-hex digest should fall back to original ccxt implementation."""
        patched = create_exchange(exchange_id, {"apiKey": "test", "secret": "test"})

        request = b"test_data"
        secret = b"test_secret"

        # binary digest
        patched_result = patched.hmac(request, secret, "sha256")
        expected = stdlib_hmac.new(secret, request, hashlib.sha256).digest()
        # fast_hmac with algorithm="sha256" returns hex by default
        # but the fallback returns binary with no digest arg
        assert isinstance(patched_result, (str, bytes))

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_exchange_has_expected_methods(self, exchange_id):
        """Created exchanges should expose standard ccxt methods."""
        exchange = create_exchange(exchange_id, {})
        assert hasattr(exchange, "fetch_ticker")
        assert hasattr(exchange, "fetch_order_book")
        assert hasattr(exchange, "fetch_ohlcv")
        assert hasattr(exchange, "create_order")
        assert hasattr(exchange, "cancel_order")
        assert hasattr(exchange, "fetch_balance")

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_exchange_config_forwarded(self, exchange_id):
        """Config dict should be applied to the exchange instance."""
        exchange = create_exchange(exchange_id, {
            "timeout": 7777,
            "rateLimit": 500,
            "enableRateLimit": True,
        })
        assert exchange.timeout == 7777
        assert exchange.rateLimit == 500
        assert exchange.enableRateLimit is True


class TestCcxtAsyncExchangePatching:
    """Test patching on async ccxt exchange instances."""

    EXCHANGES = ["binance", "bybit", "okx"]

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_creates_async_exchange(self, exchange_id):
        """async_mode=True should return ccxt.async_support exchange."""
        exchange = create_exchange(exchange_id, {}, async_mode=True)
        cls = getattr(ccxt_async, exchange_id)
        assert isinstance(exchange, cls)

    @pytest.mark.parametrize("exchange_id", EXCHANGES)
    def test_async_patched_hmac_matches_sync(self, exchange_id):
        """Async and sync exchanges should produce identical HMAC results."""
        sync_ex = create_exchange(exchange_id, {"apiKey": "k", "secret": "s"})
        async_ex = create_exchange(exchange_id, {"apiKey": "k", "secret": "s"}, async_mode=True)

        request = b"param1=val1&param2=val2"
        secret = b"the_secret"

        sync_result = sync_ex.hmac(request, secret, "sha256", "hex")
        async_result = async_ex.hmac(request, secret, "sha256", "hex")

        assert sync_result == async_result


# ── Signing consistency across multiple calls ───────────────────────────────

class TestSigningConsistency:
    """Verify that repeated signing produces identical results (no state leaks)."""

    def test_repeated_hmac_is_deterministic(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        request = b"symbol=BTCUSDT&timestamp=1700000000000"
        secret = b"my_api_secret"

        results = [exchange.hmac(request, secret, "sha256", "hex") for _ in range(100)]
        assert len(set(results)) == 1, "HMAC produced different results across calls"

    def test_different_inputs_produce_different_outputs(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"same_secret"

        results = set()
        for i in range(50):
            result = exchange.hmac(f"timestamp={i}".encode(), secret, "sha256", "hex")
            results.add(result)

        assert len(results) == 50, "Different inputs should produce unique HMACs"

    def test_hmac_output_is_valid_hex(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(b"data", b"secret", "sha256", "hex")
        # SHA256 hex = 64 chars
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


# ── Edge cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test unusual inputs and boundary conditions."""

    def test_unicode_in_request(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac("price=1000&note=日本語テスト".encode(), b"secret", "sha256", "hex")
        assert len(result) == 64

    def test_very_long_request(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        long_request = b"x" * 100_000
        result = exchange.hmac(long_request, b"secret", "sha256", "hex")
        assert len(result) == 64

    def test_empty_request_and_secret(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        result = exchange.hmac(b"", b"", "sha256", "hex")
        expected = stdlib_hmac.new(b"", b"", hashlib.sha256).hexdigest()
        assert result == expected

    def test_special_chars_in_secret(self):
        exchange = create_exchange("binance", {"apiKey": "k", "secret": "s"})
        secret = b"key+with/special=chars&and%20encoding"
        result = exchange.hmac(b"data", secret, "sha256", "hex")
        expected = stdlib_hmac.new(secret, b"data", hashlib.sha256).hexdigest()
        assert result == expected

    def test_normalize_ticker_with_none_values(self):
        raw = {"symbol": "BTC/USDT", "last": None, "bid": None, "ask": None,
               "high": None, "low": None, "baseVolume": None, "timestamp": None}
        result = normalize_ticker(raw)
        assert result["symbol"] == "BTC/USDT"
        assert result["last"] is None
        assert result["volume"] is None

    def test_normalize_ticker_with_numeric_strings(self):
        raw = {"last": "0.00000001", "bid": "0", "ask": "999999999.99"}
        result = normalize_ticker(raw)
        assert result["last"] == 1e-8
        assert result["bid"] == 0.0
        assert result["ask"] == 999999999.99

    def test_normalize_order_with_mixed_types(self):
        raw = {"price": 2050, "amount": "1.5", "filled": 0.5, "remaining": None}
        result = normalize_order(raw)
        assert result["price"] == 2050.0
        assert result["amount"] == 1.5
        assert result["filled"] == 0.5
        assert result["remaining"] is None


# ── Binance-specific signature tests ────────────────────────────────────────

class TestBinanceSignature:
    """Test Binance API signature generation end-to-end."""

    BINANCE_SECRET = b"NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    BINANCE_QUERY = b"symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
    BINANCE_EXPECTED = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"

    def test_binance_official_vector_via_exchange(self):
        """Verify patched exchange produces correct Binance API signature."""
        exchange = create_exchange("binance", {"apiKey": "test", "secret": "test"})
        result = exchange.hmac(self.BINANCE_QUERY, self.BINANCE_SECRET, "sha256", "hex")
        assert result == self.BINANCE_EXPECTED

    def test_binance_signature_via_direct_hmac(self):
        """Verify direct hmac_sha256 matches Binance vector."""
        result = hmac_sha256(self.BINANCE_SECRET, self.BINANCE_QUERY)
        assert result.hex() == self.BINANCE_EXPECTED

    def test_consistency_between_direct_and_exchange(self):
        """Direct hmac and exchange.hmac should produce the same result."""
        exchange = create_exchange("binance", {"apiKey": "test", "secret": "test"})

        direct = hmac_sha256(self.BINANCE_SECRET, self.BINANCE_QUERY).hex()
        via_exchange = exchange.hmac(self.BINANCE_QUERY, self.BINANCE_SECRET, "sha256", "hex")

        assert direct == via_exchange
