#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import decimal
import mock
import pytest

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.symbols as commons_symbols

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data as personal_data
from tests.test_utils.random_numbers import decimal_random_quantity, decimal_random_price

from tests.exchanges import backtesting_trader, backtesting_config, backtesting_exchange_manager, fake_backtesting
from tests import event_loop

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_current_crypto_currencies_values(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    assert portfolio_value_holder.get_current_crypto_currencies_values() == \
           {'BTC': constants.ONE, 'USDT': constants.ZERO}
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()},
        'ETH': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()},
        'XRP': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()},
        'DOT': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()},
        'MATIC': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()},
        'USDT': {'available': decimal_random_quantity(), 'total': decimal_random_quantity()}
    }, True)
    portfolio_manager.handle_balance_updated()

    assert portfolio_value_holder.get_current_crypto_currencies_values() == {
        'BTC': constants.ONE,
        'ETH': constants.ZERO,
        'XRP': constants.ZERO,
        'DOT': constants.ZERO,
        'MATIC': constants.ZERO,
        'USDT': constants.ZERO
    }

    exchange_manager.client_symbols.append("MATIC/BTC")
    exchange_manager.client_symbols.append("XRP/BTC")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("XRP")
    portfolio_manager.handle_mark_price_update("XRP/BTC", decimal.Decimal("0.005"))
    exchange_manager.client_symbols.append("DOT/BTC")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("DOT")
    portfolio_manager.handle_mark_price_update("DOT/BTC", decimal.Decimal("0.05"))
    exchange_manager.client_symbols.append("BTC/USDT")

    assert portfolio_value_holder.get_current_crypto_currencies_values() == {
        'BTC': constants.ONE,
        'ETH': constants.ZERO,
        'XRP': decimal.Decimal("0.005"),
        'DOT': decimal.Decimal("0.05"),
        'MATIC': constants.ZERO,
        'USDT': constants.ZERO
    }
    matic_btc_price = decimal_random_price(max_value=decimal.Decimal(0.05))
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("MATIC")
    portfolio_manager.handle_mark_price_update("MATIC/BTC", matic_btc_price)
    assert portfolio_value_holder.get_current_crypto_currencies_values() == {
        'BTC': constants.ONE,
        'ETH': constants.ZERO,
        'XRP': decimal.Decimal("0.005"),
        'DOT': decimal.Decimal("0.05"),
        'MATIC': matic_btc_price,
        'USDT': constants.ZERO
    }
    usdt_btc_price = decimal_random_price(max_value=decimal.Decimal('0.01'))
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("USDT")
    portfolio_manager.handle_mark_price_update("BTC/USDT", usdt_btc_price)
    assert portfolio_value_holder.get_current_crypto_currencies_values() == {
        'BTC': constants.ONE,
        'ETH': constants.ZERO,
        'XRP': decimal.Decimal("0.005"),
        'DOT': decimal.Decimal("0.05"),
        'MATIC': matic_btc_price,
        'USDT': constants.ONE / usdt_btc_price
    }
    eth_btc_price = decimal_random_price(max_value=constants.ONE)
    exchange_manager.client_symbols.append("ETH/BTC")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("ETH")
    portfolio_manager.handle_mark_price_update("ETH/BTC", eth_btc_price)
    assert portfolio_value_holder.get_current_crypto_currencies_values() == {
        'BTC': constants.ONE,
        'ETH': decimal.Decimal(str(eth_btc_price)),
        'XRP': decimal.Decimal("0.005"),
        'DOT': decimal.Decimal("0.05"),
        'MATIC': matic_btc_price,
        'USDT': constants.ONE / usdt_btc_price
    }


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_current_holdings_values(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    exchange_manager.client_symbols.append("ETH/BTC")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("ETH")
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("10"), 'total': decimal.Decimal("10")},
        'ETH': {'available': decimal.Decimal("100"), 'total': decimal.Decimal("100")},
        'XRP': {'available': decimal.Decimal("10000"), 'total': decimal.Decimal("10000")},
        'USDT': {'available': decimal.Decimal("1000"), 'total': decimal.Decimal("1000")}
    }, True)
    portfolio_manager.handle_balance_updated()
    assert portfolio_value_holder.get_current_holdings_values() == {
        'BTC': decimal.Decimal("10"),
        'ETH': constants.ZERO,
        'XRP': constants.ZERO,
        'USDT': constants.ZERO
    }
    def mock_get_symbol_position(symbol, side):
        mock_pos = mock.Mock()
        if symbol == "ETH/USDT":
            mock_pos.margin = decimal.Decimal("5000")
            mock_pos.is_idle.return_value = False
        elif symbol == "XRP/USDT":
            mock_pos.margin = decimal.Decimal("0.1")
            mock_pos.is_idle.return_value = False
        else:
            raise errors.ContractExistsError(f"Contract {symbol} does not exist")
        return mock_pos

    def mock_create_symbol_position(symbol, position_id):
        mock_pos = mock.Mock()
        mock_pos.position_id = position_id
        mock_pos.symbol = symbol
        mock_pos.margin = constants.ZERO
        mock_pos.is_idle.return_value = True
        return mock_pos

    with mock.patch.object(
        exchange_manager.exchange_personal_data.positions_manager,
        "_create_symbol_position",
        mock_create_symbol_position,
    ), mock.patch.object(
        exchange_manager.exchange_personal_data.positions_manager,
        "get_symbol_position",
        mock_get_symbol_position,
    ):
        portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/BTC:BTC"] = decimal.Decimal("50")
        portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/BTC"] = decimal.Decimal("50")
        # Update current_crypto_currencies_values to include ETH with the calculated price
        portfolio_value_holder.current_crypto_currencies_values["ETH"] = decimal.Decimal("50")
        portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values(init_price_fetchers=False)
        assert portfolio_value_holder.get_current_holdings_values() == {
            'BTC': decimal.Decimal("10"),
            'ETH': decimal.Decimal("5000"),
            'XRP': constants.ZERO,
            'USDT': constants.ZERO
        }
        portfolio_manager.handle_mark_price_update("XRP/USDT", 2.5)
        assert portfolio_value_holder.get_current_holdings_values() == {
            'BTC': decimal.Decimal("10"),
            'ETH': decimal.Decimal("5000"),
            'XRP': constants.ZERO,
            'USDT': constants.ZERO
        }
        portfolio_manager.handle_mark_price_update("XRP/BTC", decimal.Decimal('0.00001'))
        assert portfolio_value_holder.get_current_holdings_values() == {
            'BTC': decimal.Decimal("10"),
            'ETH': decimal.Decimal("5000"),
            'XRP': constants.ZERO,
            'USDT': constants.ZERO
        }
        exchange_manager.client_symbols.append("XRP/BTC")
        portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("XRP")
        portfolio_manager.handle_mark_price_update("XRP/BTC", decimal.Decimal('0.00001'))
        assert portfolio_value_holder.get_current_holdings_values() == {
            'BTC': decimal.Decimal(10),
            'ETH': decimal.Decimal(5000),
            'XRP': decimal.Decimal(str(0.1)),
            'USDT': constants.ZERO
        }
        exchange_manager.client_symbols.append("BTC/USDT")
        portfolio_value_holder.value_converter.missing_currency_data_in_exchange.remove("USDT")
        portfolio_manager.handle_mark_price_update("BTC/USDT", 5000)
        assert portfolio_value_holder.get_current_holdings_values() == {
            'BTC': decimal.Decimal(10),
            'ETH': decimal.Decimal(5000),
            'XRP': decimal.Decimal(str(0.1)),
            'USDT': decimal.Decimal(str(0.2))
        }


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_origin_portfolio_current_value(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    portfolio_manager.handle_profitability_recalculation(True)
    assert portfolio_value_holder.get_origin_portfolio_current_value() == decimal.Decimal(str(10))

@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_origin_portfolio_current_value_with_different_reference_market(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    portfolio_manager.reference_market = "USDT"
    portfolio_manager.handle_profitability_recalculation(True)
    assert portfolio_value_holder.get_origin_portfolio_current_value() == decimal.Decimal(str(1000))

@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_update_origin_crypto_currencies_values(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    assert portfolio_value_holder.update_origin_crypto_currencies_values("ETH/BTC", decimal.Decimal(str(0.1))) is True
    assert portfolio_value_holder.origin_crypto_currencies_values["ETH"] == decimal.Decimal(str(0.1))
    assert portfolio_value_holder.value_converter.last_prices_by_trading_pair["ETH/BTC"] == decimal.Decimal(str(0.1))
    # ETH is now priced and BTC is the reference market
    assert portfolio_value_holder.update_origin_crypto_currencies_values("ETH/BTC", decimal.Decimal(str(0.1))) is False

    assert portfolio_value_holder.update_origin_crypto_currencies_values("BTC/USDT", decimal.Decimal(str(100))) is True
    assert portfolio_value_holder.origin_crypto_currencies_values["USDT"] == \
           decimal.Decimal(constants.ONE / decimal.Decimal(100))
    assert portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] == decimal.Decimal(str(100))
    # USDT is now priced and BTC is the reference market
    assert portfolio_value_holder.update_origin_crypto_currencies_values("BTC/USDT", decimal.Decimal(str(100))) is False

    # with bridge pair (DOT/ETH -> ETH/BTC to compute DOT/BTC)
    assert portfolio_value_holder.update_origin_crypto_currencies_values("DOT/ETH", decimal.Decimal(str(0.015))) is True
    assert portfolio_value_holder.origin_crypto_currencies_values["DOT"] == \
           decimal.Decimal(str(0.015)) * decimal.Decimal(str(0.1))
    assert portfolio_value_holder.value_converter.last_prices_by_trading_pair["DOT/ETH"] == decimal.Decimal(str(0.015))
    # USDT is now priced and BTC is the reference market
    assert portfolio_value_holder.update_origin_crypto_currencies_values("DOT/ETH", decimal.Decimal(str(0.015))) \
           is False

@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_sync_portfolio_current_value_using_available_currencies_values(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder

    assert portfolio_value_holder.portfolio_current_value == constants.ZERO
    portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values()
    assert portfolio_value_holder.portfolio_current_value == decimal.Decimal(str(10))

    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.clear()
    exchange_manager.client_symbols.append("BTC/USDT")
    portfolio_manager.handle_mark_price_update("BTC/USDT", decimal.Decimal(str(100)))
    portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values()
    assert portfolio_value_holder.portfolio_current_value == decimal.Decimal(str(20)) # now includes USDT

@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "futures"], indirect=True)
async def test_get_holdings_ratio(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    symbol = "BTC/USDT"
    exchange_manager.client_symbols = [symbol]
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair[symbol] = decimal.Decimal("1000")
    # Also add the futures symbol price for value conversion
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["BTC/USDT:USDT"] = decimal.Decimal("1000")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        portfolio_current_value = decimal.Decimal("11")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio = {}
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["BTC"] = \
        personal_data.SpotAsset(name="BTC", available=decimal.Decimal("10"), total=decimal.Decimal("10"))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["USDT"] = \
        personal_data.SpotAsset(name="USDT", available=decimal.Decimal("1000"), total=decimal.Decimal("1000"))
    usdt_removed = [False]

    def mock_get_or_create_position_impl(symbol, side):
        mock_pos = mock.Mock()
        if symbol == "BTC/USDT:USDT":
            if usdt_removed[0]:
                mock_pos.margin = constants.ZERO
                mock_pos.is_idle.return_value = True
            else:
                # margin in USDT (settlement currency), which converts to 1 BTC at 1000 USDT/BTC
                mock_pos.margin = decimal.Decimal("1000")
                mock_pos.is_idle.return_value = False
        elif symbol == "BTC/XYZ:XYZ":
            mock_pos.margin = decimal.Decimal("0")
            mock_pos.is_idle.return_value = False
        else:
            raise errors.ContractExistsError(f"Contract {symbol} does not exist")
        return mock_pos

    mock_get_or_create = mock.Mock(side_effect=mock_get_or_create_position_impl)

    def mock_get_contract(pair):
        mock_contract = mock.Mock()
        mock_contract.is_one_way_position_mode.return_value = True
        return mock_contract

    with mock.patch.object(
        exchange_manager.exchange_personal_data.positions_manager,
        "_get_or_create_position",
        mock_get_or_create,
    ), mock.patch.object(
        exchange_manager.exchange,
        "get_pair_future_contract", # TODO update this mock to use get_pair_contract to support options
        mock_get_contract,
    ):
        exchange_manager.exchange_config.traded_symbols = [commons_symbols.parse_symbol("BTC/USDT")]
        assert portfolio_value_holder.get_holdings_ratio("BTC") == decimal.Decimal('0.9090909090909090909090909091')
        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=False) \
               == decimal.Decimal('0.9090909090909090909090909091')
        assert portfolio_value_holder.get_holdings_ratio("USDT") == decimal.Decimal('0.09090909090909090909090909091')

        exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio.pop("USDT")
        usdt_removed[0] = True
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
            portfolio_current_value = decimal.Decimal("10")
        assert portfolio_value_holder.get_holdings_ratio("BTC") == constants.ONE
        # add ETH and try to get ratio without symbol price
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio.\
            get_currency_portfolio("ETH").total = decimal.Decimal(10)
        # force not backtesting mode
        exchange_manager.is_backtesting = False
        # force add symbol in exchange symbols
        exchange_manager.client_symbols.append("ETH/BTC")
        if not exchange_manager.is_spot_only:
            with pytest.raises(errors.ContractExistsError):
                _ = portfolio_value_holder.get_holdings_ratio("ETH")
        else:
            with pytest.raises(errors.MissingPriceDataError):
                _ = portfolio_value_holder.get_holdings_ratio("ETH")
        # let channel register proceed
        await asyncio_tools.wait_asyncio_next_cycle()
        assert portfolio_value_holder.get_holdings_ratio("BTC") == constants.ONE
        assert portfolio_value_holder.get_holdings_ratio("USDT") == constants.ZERO
        assert portfolio_value_holder.get_holdings_ratio("XYZ") == constants.ZERO

        # without traded_symbols
        exchange_manager.exchange_config.traded_symbols.clear()
        assert portfolio_value_holder.get_holdings_ratio("BTC", traded_symbols_only=True) == constants.ZERO

        # with traded_symbols
        exchange_manager.exchange_config.traded_symbols.extend([
            commons_symbols.parse_symbol("BTC/USDT"), commons_symbols.parse_symbol("ETH/USDT")
        ])
        assert portfolio_value_holder.get_holdings_ratio("BTC", traded_symbols_only=True) == constants.ONE
 
@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_holdings_ratio_with_include_assets_in_open_orders(backtesting_trader):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    symbol = "BTC/USDT"
    has_eth_position = False
    exchange_manager.client_symbols = [symbol]
    exchange_manager.exchange_config.traded_symbols = [commons_symbols.parse_symbol("BTC/USDT")]
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair[symbol] = decimal.Decimal("1000")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["BTC/USDT:BTC"] = decimal.Decimal("1000")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["BTC/USDT:USDT"] = decimal.Decimal("1000")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["ETH/USDT"] = decimal.Decimal("100")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["ETH/USDT:BTC"] = decimal.Decimal("100")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        value_converter.last_prices_by_trading_pair["ETH/BTC:BTC"] = decimal.Decimal("0.1")
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
        portfolio_current_value = decimal.Decimal("11")
    exchange_manager.exchange_personal_data.portfolio_manager.reference_market = "BTC"
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio = {}
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["BTC"] = \
        personal_data.SpotAsset(name="BTC", available=decimal.Decimal("10"), total=decimal.Decimal("10"))
    exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["USDT"] = \
        personal_data.SpotAsset(name="USDT", available=decimal.Decimal("1000"), total=decimal.Decimal("1000"))
    def mock_get_or_create_position_impl(symbol, side):
        mock_pos = mock.Mock()
        if symbol == "BTC/USDT:BTC":
            mock_pos.margin = decimal.Decimal("10") # equivalent to the 10 BTC in the spot portfolio
            mock_pos.is_idle.return_value = False
        if symbol == "BTC/USDT:USDT":
            mock_pos.margin = decimal.Decimal("1000") # 1000 USDT margin, converts to 1 BTC at 1000 USDT/BTC
            mock_pos.is_idle.return_value = False
        elif symbol == "ETH/USDT:BTC":
            mock_pos.margin = decimal.Decimal("1") if has_eth_position else constants.ZERO # 1 BTC margin (settlement is BTC)
            mock_pos.is_idle.return_value = False
        elif symbol == "ETH/BTC:BTC":
            mock_pos.margin = decimal.Decimal("1") if has_eth_position else constants.ZERO # 1 BTC margin (settlement is BTC)
            mock_pos.is_idle.return_value = False
        else:
            raise errors.ContractExistsError(f"Contract {symbol} does not exist")
        return mock_pos

    mock_get_or_create = mock.Mock(side_effect=mock_get_or_create_position_impl)

    def mock_get_contract(pair):
        mock_contract = mock.Mock()
        mock_contract.is_one_way_position_mode.return_value = True
        return mock_contract

    with mock.patch.object(
        exchange_manager.exchange_personal_data.positions_manager,
        "_get_or_create_position",
        mock_get_or_create,
    ), mock.patch.object(
        exchange_manager.exchange,
        "get_pair_future_contract",
        mock_get_contract,
    ):
        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=False) \
               == decimal.Decimal('0.9090909090909090909090909091')
        assert portfolio_value_holder.get_holdings_ratio("USDT", include_assets_in_open_orders=False) \
               == decimal.Decimal('0.09090909090909090909090909091')

        # no open order
        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.9090909090909090909090909091')
        assert portfolio_value_holder.get_holdings_ratio("USDT", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.09090909090909090909090909091')

        order_1 = mock.Mock(
            order_id="1", symbol="BTC/USDT", origin_quantity=decimal.Decimal("1"), total_cost=decimal.Decimal('1000'),
            status=enums.OrderStatus.OPEN, side=enums.TradeOrderSide.BUY
        )
        order_2 = mock.Mock(
            order_id="2", symbol="ETH/USDT", origin_quantity=decimal.Decimal("2"), total_cost=decimal.Decimal('100'),
            status=enums.OrderStatus.OPEN, side=enums.TradeOrderSide.BUY
        )
        order_3 = mock.Mock(
            order_id="3", symbol="XRP/ETH", origin_quantity=decimal.Decimal("100"), total_cost=decimal.Decimal('0.001'),
            status=enums.OrderStatus.OPEN, side=enums.TradeOrderSide.SELL
        )
        # open orders
        await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order_1)
        await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order_2)
        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=False) \
               == decimal.Decimal('0.9090909090909090909090909091')
        assert portfolio_value_holder.get_holdings_ratio("ETH", include_assets_in_open_orders=False) \
               == decimal.Decimal('0')
        assert portfolio_value_holder.get_holdings_ratio("USDT", include_assets_in_open_orders=False) \
               == decimal.Decimal('0.09090909090909090909090909091')

        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=True) \
               == decimal.Decimal('1')
        assert portfolio_value_holder.get_holdings_ratio("ETH", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.01818181818181818181818181818')
        assert portfolio_value_holder.get_holdings_ratio("USDT", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.09090909090909090909090909091')

        await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order_3)
        assert portfolio_value_holder.get_holdings_ratio("BTC", include_assets_in_open_orders=True) \
               == decimal.Decimal('1')
        assert portfolio_value_holder.get_holdings_ratio("ETH", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.01819090909090909090909090909')
        assert portfolio_value_holder.get_holdings_ratio("USDT", include_assets_in_open_orders=True) \
               == decimal.Decimal('0.09090909090909090909090909091')

        # without traded_symbols
        exchange_manager.exchange_config.traded_symbols.clear()
        assert portfolio_value_holder.get_holdings_ratio(
            "BTC", traded_symbols_only=True, include_assets_in_open_orders=True
        ) == constants.ZERO

        # with traded_symbols
        exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio["ETH"] = \
            personal_data.SpotAsset(name="ETH", available=decimal.Decimal("10"), total=decimal.Decimal("10"))
        has_eth_position = True
        exchange_manager.exchange_config.traded_symbols.extend([
            commons_symbols.parse_symbol("BTC/USDT")
        ])
        assert portfolio_value_holder.get_holdings_ratio(
            "BTC", traded_symbols_only=True, include_assets_in_open_orders=True
        ) == constants.ONE
        # 10 ETH (portfolio) + 2.001 (orders) in BTC / 11 = 0.1091
        assert portfolio_value_holder.get_holdings_ratio(
                "ETH", traded_symbols_only=True, include_assets_in_open_orders=True
        ) == decimal.Decimal('0.1091')
            
        # ETH now in traded assets
        exchange_manager.exchange_config.traded_symbols.extend([
            commons_symbols.parse_symbol("ETH/USDT")
        ])
        # 12.001 ETH in BTC / 12 total = 0.1000083
        assert portfolio_value_holder.get_holdings_ratio(
                "ETH", traded_symbols_only=True, include_assets_in_open_orders=True
        ) == decimal.Decimal('0.1000083333333333333333333333')  # ETH now taken into account in total value
            
        # ETH now taken into account in total value: BTC % of holdings is not 1 anymore (as ETH takes a part of this %)
        assert portfolio_value_holder.get_holdings_ratio(
            "BTC", traded_symbols_only=True, include_assets_in_open_orders=True
        ) == decimal.Decimal('0.9166666666666666666666666667')


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
@pytest.mark.parametrize("unit,coins_whitelist", [
    ("BTC", None),
    ("BTC", ["BTC"]),
    ("BTC", ["USDT"]),
    ("BTC", ["BTC", "ETH"]),
])
async def test_get_traded_assets_holdings_value(backtesting_trader, unit, coins_whitelist):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("10"), 'total': decimal.Decimal("10")},
        'USDT': {'available': decimal.Decimal("1000"), 'total': decimal.Decimal("1000")},
        'ETH': {'available': decimal.Decimal("5"), 'total': decimal.Decimal("5")},
    }, True)
    
    exchange_manager.exchange_config.traded_symbols = [commons_symbols.parse_symbol("BTC/USDT")]
    exchange_manager.client_symbols.append("BTC/USDT")
    portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("1000")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    
    result = portfolio_value_holder.get_traded_assets_holdings_value(unit, coins_whitelist)
    
    # Verify result is a decimal and non-negative
    assert isinstance(result, decimal.Decimal)
    assert result >= constants.ZERO


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
@pytest.mark.parametrize("currency,traded_symbols_only,include_assets_in_open_orders,coins_whitelist,expected_ratio_zero", [
    ("BTC", False, False, None, False),
    ("BTC", True, False, None, False),
    ("USDT", False, False, None, False),
    ("BTC", False, True, None, False),
    ("BTC", True, True, ["BTC"], False),
    ("XYZ", False, False, None, True),
])
async def test_get_holdings_ratio_from_portfolio(backtesting_trader, currency, traded_symbols_only, include_assets_in_open_orders, coins_whitelist, expected_ratio_zero):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("10"), 'total': decimal.Decimal("10")},
        'USDT': {'available': decimal.Decimal("1000"), 'total': decimal.Decimal("1000")},
    }, True)
    
    exchange_manager.exchange_config.traded_symbols = [commons_symbols.parse_symbol("BTC/USDT")]
    exchange_manager.client_symbols.append("BTC/USDT")
    portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("1000")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values(init_price_fetchers=False)
    
    result = portfolio_value_holder._get_holdings_ratio_from_portfolio(
        currency, traded_symbols_only, include_assets_in_open_orders, coins_whitelist
    )
    
    assert isinstance(result, decimal.Decimal)
    assert result >= constants.ZERO
    assert result <= constants.ONE
    if expected_ratio_zero:
        assert result == constants.ZERO


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
@pytest.mark.parametrize("coins_whitelist,traded_symbols_only,use_portfolio_current_value", [
    (None, False, True),
    (None, True, False),
    (["BTC", "USDT"], False, False),
    (["BTC"], True, False),
])
async def test_get_total_holdings_value(backtesting_trader, coins_whitelist, traded_symbols_only, use_portfolio_current_value):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    portfolio_manager.portfolio.update_portfolio_from_balance({
        'BTC': {'available': decimal.Decimal("10"), 'total': decimal.Decimal("10")},
        'USDT': {'available': decimal.Decimal("1000"), 'total': decimal.Decimal("1000")},
    }, True)
    
    exchange_manager.exchange_config.traded_symbols = [commons_symbols.parse_symbol("BTC/USDT")]
    exchange_manager.client_symbols.append("BTC/USDT")
    portfolio_value_holder.value_converter.last_prices_by_trading_pair["BTC/USDT"] = decimal.Decimal("1000")
    portfolio_value_holder.value_converter.missing_currency_data_in_exchange.discard("USDT")
    portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values(init_price_fetchers=False)
    
    result = portfolio_value_holder._get_total_holdings_value(coins_whitelist, traded_symbols_only)
    
    assert isinstance(result, decimal.Decimal)
    assert result >= constants.ZERO
    if use_portfolio_current_value and not coins_whitelist and not traded_symbols_only:
        assert result == portfolio_value_holder.portfolio_current_value


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
@pytest.mark.parametrize("currency,order_symbol,order_side,order_quantity,order_cost,expected_delta", [
    ("BTC", "BTC/USDT", enums.TradeOrderSide.BUY, decimal.Decimal("1"), decimal.Decimal("1000"), decimal.Decimal("1")),
    ("USDT", "BTC/USDT", enums.TradeOrderSide.SELL, decimal.Decimal("1"), decimal.Decimal("1000"), decimal.Decimal("1000")),
    ("ETH", "ETH/BTC", enums.TradeOrderSide.BUY, decimal.Decimal("2"), decimal.Decimal("0.1"), decimal.Decimal("2")),
    ("BTC", "ETH/BTC", enums.TradeOrderSide.SELL, decimal.Decimal("2"), decimal.Decimal("0.1"), decimal.Decimal("0.1")),
    ("XYZ", "BTC/USDT", enums.TradeOrderSide.BUY, decimal.Decimal("1"), decimal.Decimal("1000"), constants.ZERO),
])
async def test_get_orders_delta(backtesting_trader, currency, order_symbol, order_side, order_quantity, order_cost, expected_delta):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    mock_order = mock.Mock()
    mock_order.symbol = order_symbol
    mock_order.side = order_side
    mock_order.origin_quantity = order_quantity
    mock_order.total_cost = order_cost
    mock_order.status = enums.OrderStatus.OPEN
    
    with mock.patch.object(
        portfolio_manager.exchange_manager.exchange_personal_data.orders_manager,
        "get_open_orders",
        return_value=[mock_order]
    ):
        result = portfolio_value_holder._get_orders_delta(currency)
        
        assert isinstance(result, decimal.Decimal)
        assert result == expected_delta


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
@pytest.mark.parametrize("order_side,order_quantity,filled_quantity,order_price,expected_value", [
    # Buy order: (quantity - filled) * price = (10 - 0) * 50 = 500
    (enums.TradeOrderSide.BUY, decimal.Decimal("10"), decimal.Decimal("0"), decimal.Decimal("50"), decimal.Decimal("500")),
    # Buy order partially filled: (10 - 3) * 50 = 350
    (enums.TradeOrderSide.BUY, decimal.Decimal("10"), decimal.Decimal("3"), decimal.Decimal("50"), decimal.Decimal("350")),
    # Sell order: decreases value by (quantity - filled) * price = -500
    (enums.TradeOrderSide.SELL, decimal.Decimal("10"), decimal.Decimal("0"), decimal.Decimal("50"), decimal.Decimal("-500")),
    # Sell order partially filled: -(10 - 5) * 50 = -250
    (enums.TradeOrderSide.SELL, decimal.Decimal("10"), decimal.Decimal("5"), decimal.Decimal("50"), decimal.Decimal("-250")),
])
async def test_get_open_orders_value_for_symbol(backtesting_trader, order_side, order_quantity, filled_quantity, order_price, expected_value):
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    test_symbol = "slug/USDC:USDC-260331-0-YES"
    
    # Create a real order object based on the side
    if order_side == enums.TradeOrderSide.BUY:
        order = personal_data.BuyLimitOrder(trader)
    else:
        order = personal_data.SellLimitOrder(trader)
    
    order.update(order_type=enums.TraderOrderType.BUY_LIMIT if order_side == enums.TradeOrderSide.BUY else enums.TraderOrderType.SELL_LIMIT,
                 symbol=test_symbol,
                 current_price=order_price,
                 quantity=order_quantity,
                 price=order_price)
    order.filled_quantity = filled_quantity
    
    with mock.patch.object(
        portfolio_manager.exchange_manager.exchange_personal_data.orders_manager,
        "get_open_orders",
        return_value=[order]
    ):
        result = portfolio_value_holder._get_open_orders_value_for_symbol(test_symbol)
        
        assert isinstance(result, decimal.Decimal)
        assert result == expected_value


@pytest.mark.parametrize("backtesting_exchange_manager", ["spot", "margin", "futures", "options"], indirect=True)
async def test_get_open_orders_value_for_symbol_multiple_orders(backtesting_trader):
    """Test that multiple orders for the same symbol are summed correctly."""
    config, exchange_manager, trader = backtesting_trader
    portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
    portfolio_value_holder = portfolio_manager.portfolio_value_holder
    
    test_symbol = "slug/USDC:USDC-260331-0-YES"
    
    # Buy order: 10 * 50 = 500
    buy_order = personal_data.BuyLimitOrder(trader)
    buy_order.update(order_type=enums.TraderOrderType.BUY_LIMIT,
                     symbol=test_symbol,
                     current_price=decimal.Decimal("50"),
                     quantity=decimal.Decimal("10"),
                     price=decimal.Decimal("50"))
    buy_order.filled_quantity = decimal.Decimal("0")
    
    # Sell order: -5 * 40 = -200
    sell_order = personal_data.SellLimitOrder(trader)
    sell_order.update(order_type=enums.TraderOrderType.SELL_LIMIT,
                      symbol=test_symbol,
                      current_price=decimal.Decimal("40"),
                      quantity=decimal.Decimal("5"),
                      price=decimal.Decimal("40"))
    sell_order.filled_quantity = decimal.Decimal("0")
    
    # Net value: 500 - 200 = 300
    with mock.patch.object(
        portfolio_manager.exchange_manager.exchange_personal_data.orders_manager,
        "get_open_orders",
        return_value=[buy_order, sell_order]
    ):
        result = portfolio_value_holder._get_open_orders_value_for_symbol(test_symbol)
        
        assert isinstance(result, decimal.Decimal)
        assert result == decimal.Decimal("300")

