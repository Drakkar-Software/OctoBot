import pytest

from octobot_connectors import (
    CcxtConnector,
    ExchangeConfig,
    ExchangeCredentials,
    ExchangeTypes,
    TimeFrame,
    TradeOrderSide,
    TraderOrderType,
    OrderStatus,
)


def test_exchange_config_basic():
    config = ExchangeConfig(exchange_name="binance")
    assert config.exchange_name == "binance"
    assert not config.is_future
    assert not config.is_sandboxed


def test_exchange_config_future():
    config = ExchangeConfig(exchange_name="binanceusdm", is_future=True)
    assert config.exchange_name == "binanceusdm"
    assert config.is_future


def test_exchange_credentials():
    creds = ExchangeCredentials(api_key="key123", api_secret="secret456")
    assert creds.api_key == "key123"
    assert creds.api_secret == "secret456"
    assert creds.has_credentials()


def test_exchange_credentials_empty():
    creds = ExchangeCredentials()
    assert not creds.has_credentials()


def test_ccxt_connector_creation():
    config = ExchangeConfig(exchange_name="binance")
    connector = CcxtConnector(config=config)
    assert connector.exchange_name == "binance"


def test_trade_order_side_values():
    assert TradeOrderSide.Buy.value == "buy"
    assert TradeOrderSide.Sell.value == "sell"


def test_order_status_values():
    assert OrderStatus.Open.value == "open"
    assert OrderStatus.Canceled.value == "canceled"
    assert OrderStatus.Filled.value == "filled"


def test_time_frame_values():
    assert TimeFrame.OneMinute.value == "1m"
    assert TimeFrame.OneHour.value == "1h"
    assert TimeFrame.OneDay.value == "1d"


def test_exchange_types():
    assert ExchangeTypes.Spot.value == "spot"
    assert ExchangeTypes.Future.value == "future"


def test_trader_order_type_ccxt_mapping():
    assert TraderOrderType.BuyLimit.ccxt_type() == "limit"
    assert TraderOrderType.BuyMarket.ccxt_type() == "market"
    assert TraderOrderType.SellLimit.ccxt_type() == "limit"
    assert TraderOrderType.SellMarket.ccxt_type() == "market"
