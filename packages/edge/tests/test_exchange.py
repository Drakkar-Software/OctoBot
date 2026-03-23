"""Tests for octobot_edge.exchange — verifies exchange factory and patching."""
from unittest.mock import MagicMock, patch

import pytest

from octobot_edge.exchange.client import create_exchange, _patch_signing
from octobot_edge.exchange.normalize import normalize_ticker, normalize_order


class TestCreateExchange:
    """Test the exchange factory."""

    def test_creates_sync_exchange(self):
        """create_exchange should return a ccxt exchange instance."""
        exchange = create_exchange("binance", {})
        import ccxt
        assert isinstance(exchange, ccxt.binance)

    def test_creates_async_exchange(self):
        """create_exchange with async_mode=True should return async exchange."""
        exchange = create_exchange("binance", {}, async_mode=True)
        import ccxt.async_support as ccxt_async
        assert isinstance(exchange, ccxt_async.binance)

    def test_passes_config(self):
        """Config dict should be forwarded to ccxt constructor."""
        exchange = create_exchange("binance", {"timeout": 5000})
        assert exchange.timeout == 5000

    def test_unknown_exchange_raises(self):
        """Requesting a non-existent exchange should raise AttributeError."""
        with pytest.raises(AttributeError):
            create_exchange("nonexistent_exchange_xyz", {})


class TestPatchSigning:
    """Test the HMAC patching logic."""

    def test_patch_overrides_hmac(self):
        """After patching, exchange.hmac should be our custom function."""
        exchange = MagicMock()
        exchange.hmac = MagicMock(return_value="original")
        _patch_signing(exchange)
        # The hmac attribute should now be our fast_hmac wrapper
        assert callable(exchange.hmac)
        assert exchange.hmac.__name__ == "fast_hmac"

    def test_patch_falls_back_for_non_sha256(self):
        """For algorithms other than sha256, should fall back to original."""
        exchange = MagicMock()
        original_hmac = MagicMock(return_value="original_result")
        exchange.hmac = original_hmac
        _patch_signing(exchange)
        result = exchange.hmac("request", "secret", "sha384", "hex")
        original_hmac.assert_called_once_with("request", "secret", "sha384", "hex")
        assert result == "original_result"


class TestNormalizeTicker:
    """Test ticker normalization."""

    def test_normalizes_complete_ticker(self):
        raw = {
            "symbol": "BTC/USDT",
            "last": "50000.0",
            "bid": "49999.0",
            "ask": "50001.0",
            "high": "51000.0",
            "low": "49000.0",
            "baseVolume": "1234.5",
            "timestamp": 1700000000000,
        }
        result = normalize_ticker(raw)
        assert result["symbol"] == "BTC/USDT"
        assert result["last"] == 50000.0
        assert result["bid"] == 49999.0
        assert result["ask"] == 50001.0
        assert result["volume"] == 1234.5
        assert result["timestamp"] == 1700000000000

    def test_handles_missing_fields(self):
        result = normalize_ticker({})
        assert result["symbol"] is None
        assert result["last"] is None
        assert result["volume"] is None

    def test_handles_non_numeric(self):
        result = normalize_ticker({"last": "invalid"})
        assert result["last"] is None


class TestNormalizeOrder:
    """Test order normalization."""

    def test_normalizes_complete_order(self):
        raw = {
            "id": "12345",
            "symbol": "ETH/USDT",
            "side": "buy",
            "type": "limit",
            "price": "3000.0",
            "amount": "1.5",
            "filled": "0.5",
            "remaining": "1.0",
            "status": "open",
            "timestamp": 1700000000000,
        }
        result = normalize_order(raw)
        assert result["id"] == "12345"
        assert result["symbol"] == "ETH/USDT"
        assert result["side"] == "buy"
        assert result["type"] == "limit"
        assert result["price"] == 3000.0
        assert result["amount"] == 1.5
        assert result["filled"] == 0.5
        assert result["remaining"] == 1.0
        assert result["status"] == "open"
        assert result["timestamp"] == 1700000000000

    def test_handles_missing_fields(self):
        result = normalize_order({})
        assert result["id"] is None
        assert result["symbol"] is None
        assert result["price"] is None
        assert result["remaining"] is None
