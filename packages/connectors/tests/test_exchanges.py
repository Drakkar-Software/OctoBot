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


def test_exchange_config_future():
    config = ExchangeConfig(exchange_name="binanceusdm", is_future=True)
    assert config.exchange_name == "binanceusdm"
    assert config.is_future


def test_exchange_credentials():
    creds = ExchangeCredentials(api_key="key123", secret="secret456")
    assert creds.api_key == "key123"
    assert creds.has_credentials()


def test_exchange_credentials_empty():
    creds = ExchangeCredentials()
    assert not creds.has_credentials()


def test_ccxt_connector_creation():
    config = ExchangeConfig(exchange_name="binance")
    connector = CcxtConnector(config=config)
    assert connector.exchange_name == "binance"
    assert connector.get_name() == "binance"


def test_trade_order_side_values():
    buy = TradeOrderSide("buy")
    sell = TradeOrderSide("sell")
    assert buy.value() == "buy"
    assert sell.value() == "sell"


def test_order_status_values():
    open_s = OrderStatus("open")
    canceled = OrderStatus("canceled")
    filled = OrderStatus("filled")
    assert open_s.value() == "open"
    assert canceled.value() == "canceled"
    assert filled.value() == "filled"
    assert not open_s.is_closed()
    assert filled.is_closed()


def test_time_frame_values():
    tf1m = TimeFrame("1m")
    tf1h = TimeFrame("1h")
    tf1d = TimeFrame("1d")
    assert tf1m.to_ccxt_value() == "1m"
    assert tf1h.to_ccxt_value() == "1h"
    assert tf1d.to_ccxt_value() == "1d"
    assert tf1m.to_seconds() == 60
    assert tf1h.to_seconds() == 3600


def test_exchange_types():
    spot = ExchangeTypes("spot")
    future = ExchangeTypes("future")
    assert spot.value() == "spot"
    assert future.value() == "future"


def test_trader_order_type_ccxt_mapping():
    buy_limit = TraderOrderType("buy_limit")
    buy_market = TraderOrderType("buy_market")
    assert buy_limit.value() == "buy_limit"
    assert buy_market.value() == "buy_market"
