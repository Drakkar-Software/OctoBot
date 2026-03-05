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
#  Lesser General License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import uuid
import typing
import copy
import decimal

import octobot_commons.logging as logging
import octobot_commons.symbols as common_symbols

import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.util.test_tools.exchange_data as exchange_data_import
import octobot_trading.exchanges as exchanges
import octobot_trading.personal_data as personal_data
import octobot_trading.storage as storage
import octobot_trading.exchange_data

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges.exchange_manager


TO_KEEP_POSITION_KEYS = [
    enums.ExchangeConstantsPositionColumns.LOCAL_ID.value,  # to fetch position
    enums.ExchangeConstantsPositionColumns.SYMBOL.value,  # to fetch position
    enums.ExchangeConstantsPositionColumns.LEVERAGE.value,  # to keep user configured leverage
]


# Utility functions to update ExchangeManager from exchange_data


async def initialize_trader_positions_and_orders_from_exchange_data(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData,
    price_by_symbol: dict[str, float],
    ignore_orders_and_trades: bool,
    lock_chained_orders_funds: bool,
    as_simulator: bool,
):
    exchange_manager.trader.is_enabled = True
    await exchange_manager.trader.initialize()
    _set_current_prices(exchange_manager, exchange_data, price_by_symbol)
    _initialize_trading_portfolio_values(exchange_manager)
    if not ignore_orders_and_trades:
        if exchange_data.trades:
            await set_trades(exchange_manager, exchange_data)
        if exchange_data.orders_details.open_orders and \
                exchange_data.orders_details.open_orders[0].get(
                    constants.STORAGE_ORIGIN_VALUE, {}
                ).get(enums.ExchangeConstantsOrderColumns.TYPE.value):
            await set_open_orders(exchange_manager, exchange_data)
        if lock_chained_orders_funds:
            await _lock_missing_orders_chained_orders_funds_in_portfolio(
                exchange_manager, exchange_data
            )
        set_positions_and_contracts(exchange_manager, exchange_data)
        if exchange_manager.is_future and not as_simulator:
            # only rely on exchange-fetched position data
            exchange_manager.exchange_personal_data.positions_manager.is_exclusively_using_exchange_position_details = True


def _set_current_prices(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData,
    price_by_symbol: dict[str, float],
):
    value_converter = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.value_converter
    added_symbols = set()
    for market in exchange_data.markets:
        price = price_by_symbol.get(market.symbol)
        if price is not None:
            price = decimal.Decimal(str(price))
            exchanges.force_set_mark_price(exchange_manager, market.symbol, price)
            value_converter.update_last_price(market.symbol, price)
            added_symbols.add(market.symbol)
    ref_market = exchange_manager.exchange_personal_data.portfolio_manager.reference_market
    for asset, value in exchange_data.portfolio_details.asset_values.items():
        if asset == ref_market:
            continue
        # include fetched portfolio assets values to be able to value them in ref market in case they
        # are not already added from traded pairs
        value_symbol = common_symbols.merge_currencies(asset, ref_market)
        decimal_value = decimal.Decimal(str(value))
        if value_symbol not in added_symbols:
            exchanges.force_set_mark_price(exchange_manager, value_symbol, decimal_value)
            value_converter.update_last_price(value_symbol, decimal_value)
            added_symbols.add(value_symbol)


async def set_trades(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData
):
    for trade_dict in exchange_data.trades:
        trade = personal_data.create_trade_from_dict(exchange_manager.trader, trade_dict)
        trade.trade_id = trade.trade_id or str(uuid.uuid4())
        exchange_manager.exchange_personal_data.trades_manager.upsert_trade_instance(trade)


async def set_open_orders(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData
):
    pending_groups = {}
    for order_details in exchange_data.orders_details.open_orders:
        if constants.STORAGE_ORIGIN_VALUE in order_details:
            order = personal_data.create_order_from_order_raw_in_storage_details_without_related_elements(exchange_manager, order_details)
            await personal_data.create_orders_storage_related_elements(
                order, order_details, exchange_manager, pending_groups
            )
        else:
            # simple order dict (order just fetched from exchange)
            order = personal_data.create_order_instance_from_raw(exchange_manager.trader, order_details)
        await exchange_manager.exchange_personal_data.orders_manager.upsert_order_instance(order)


def set_positions_and_contracts(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData
):
    initialize_future_contracts(exchange_manager, exchange_data)
    for position_details in exchange_data.positions:
        if not is_cleared_position(position_details.position):
            position = personal_data.create_position_instance_from_dict(
                exchange_manager.trader, copy.copy(position_details.position)
            )
            position.position_id = exchange_manager.exchange_personal_data.positions_manager.create_position_id(
                position
            )
            exchange_manager.exchange_personal_data.positions_manager.add_position(position)


def initialize_future_contracts(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData,
):
    for position_data in exchange_data.positions:
        if position_data.contract:
            octobot_trading.exchange_data.update_future_contract_from_dict(exchange_manager, position_data.contract)


def is_cleared_position(position_dict: dict) -> bool:
    for key in position_dict:
        if key not in TO_KEEP_POSITION_KEYS:
            return False
    return True


def _initialize_trading_portfolio_values(exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager"):
    if not exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio:
        # portfolio is not initialized, skip portfolio values initialization
        return
    portfolio_value_holder = exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder
    try:
        # ensure portfolio_manager.portfolio_current_value is initialized
        portfolio_value_holder.sync_portfolio_current_value_using_available_currencies_values(
            init_price_fetchers=False
        )
        portfolio_value = portfolio_value_holder.portfolio_current_value
        if not portfolio_value or portfolio_value <= constants.ZERO:
            if _should_have_initialized_portfolio_values(exchange_manager):
                # should not happen (if it does, holding ratios using portfolio_value can't be computed)
                # This is not critial but should be fixed if seen
                logging.get_logger("ExchangeUtil").error(
                    f"[{exchange_manager.exchange_name}] Portfolio current value can't be initialized: {portfolio_value=}"
                )
            else:
                logging.get_logger("ExchangeUtil").info(
                    f"[{exchange_manager.exchange_name}] Portfolio current value not initialized: no traded asset holdings in portfolio"
                )
    except Exception as err:
        logging.get_logger("ExchangeUtil").exception(
            err, True, f"Error when initializing trading portfolio values: {err}"
        )


def _should_have_initialized_portfolio_values(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager"
) -> bool:
    portfolio_assets = [
        asset
        for asset, values in exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_manager.portfolio.portfolio.items() 
        if values.total > constants.ZERO
    ]
    if any(coin in portfolio_assets for coin in exchanges.get_traded_assets(exchange_manager)):
        return True
    return False


async def _lock_missing_orders_chained_orders_funds_in_portfolio(
    exchange_manager: "octobot_trading.exchanges.exchange_manager.ExchangeManager",
    exchange_data: exchange_data_import.ExchangeData
):
    groups = {}
    for base_order in exchange_data.orders_details.missing_orders:
        for chained_order_dict in base_order.get(enums.StoredOrdersAttr.CHAINED_ORDERS.value, []):
            chained_order = await personal_data.create_order_from_order_storage_details(
                storage.orders_storage.from_order_document(chained_order_dict), exchange_manager, groups
            )
            if chained_order.update_with_triggering_order_fees and (base_order_exchange_id :=
                base_order.get(constants.STORAGE_ORIGIN_VALUE, {})
                .get(enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value)
            ):
                trade = personal_data.aggregate_trades_by_exchange_order_id(
                    exchange_manager.exchange_personal_data.trades_manager.get_trades(exchange_order_id=base_order_exchange_id)
                ).get(base_order_exchange_id)
                if trade:
                    chained_order.update_quantity_with_order_fees(trade)
            exchange_manager.exchange_personal_data.portfolio_manager.portfolio.update_portfolio_available(
                chained_order, is_new_order=True
            )


def get_positions_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return set(get_positions_by_symbol(exchange_data))


def get_orders_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return set(
        order[constants.STORAGE_ORIGIN_VALUE][enums.ExchangeConstantsOrderColumns.SYMBOL.value]
        for order in exchange_data.orders_details.open_orders + exchange_data.orders_details.missing_orders
        if order.get(constants.STORAGE_ORIGIN_VALUE, {}).get(
            enums.ExchangeConstantsOrderColumns.SYMBOL.value
        )
    )


def get_orders_and_positions_symbols(exchange_data: exchange_data_import.ExchangeData) -> set[str]:
    return get_orders_symbols(exchange_data).union(get_positions_symbols(exchange_data))


def get_positions_by_symbol(exchange_data: exchange_data_import.ExchangeData) -> dict[str, list[dict]]:
    return {
        position_details.position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]:
            [
                symbol_position_details.position
                for symbol_position_details in exchange_data.positions
                if symbol_position_details.position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value) ==
                   position_details.position[enums.ExchangeConstantsPositionColumns.SYMBOL.value]
            ]
        for position_details in exchange_data.positions
        if enums.ExchangeConstantsPositionColumns.SYMBOL.value in position_details.position
    }
