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
import typing

import octobot_commons.logging as logging
import octobot_commons.databases as databases
import octobot_commons.constants as common_constants
import octobot_commons.signals as commons_signals

import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.storage as storage
import octobot_trading.enums as trading_enums
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchanges.util.exchange_util as exchange_util


def get_required_candles_count(trading_mode_class, tentacles_setup_config):
    return tentacles_manager_api.get_tentacle_config(tentacles_setup_config, trading_mode_class).get(
        constants.CONFIG_CANDLES_HISTORY_SIZE_KEY,
        common_constants.DEFAULT_IGNORED_VALUE
    )


async def clear_simulated_orders_cache(trading_mode):
    await basic_keywords.clear_orders_cache(
        databases.RunDatabasesProvider.instance().get_orders_db(
            trading_mode.bot_id,
            storage.get_account_type_suffix_from_exchange_manager(trading_mode.exchange_manager),
            trading_mode.exchange_manager.exchange_name
        )
    )


async def clear_plotting_cache(trading_mode):
    await basic_keywords.clear_symbol_plot_cache(
        databases.RunDatabasesProvider.instance().get_symbol_db(
            trading_mode.bot_id,
            trading_mode.exchange_manager.exchange_name, trading_mode.symbol
        )
    )


def get_assets_requiring_extra_price_data_to_convert(exchange_manager, sellable_assets: list, target_asset: str) -> set:
    missing_price_assets = set()
    for asset in sellable_assets:
        portfolio = exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
        if asset != target_asset and asset in portfolio and portfolio[asset].available:
            try:
                if exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
                   value_converter.evaluate_value(
                       asset, constants.ONE, raise_error=True, target_currency=target_asset, init_price_fetchers=False
                   ) == constants.ZERO:
                    # 0 is default value in backtesting
                    missing_price_assets.add(asset)
            except errors.MissingPriceDataError:
                # converter is not enough
                missing_price_assets.add(asset)
    return missing_price_assets


async def convert_assets_to_target_asset(
    trading_mode, sellable_assets: list, target_asset: str, tickers: dict,
    dependencies: typing.Optional[commons_signals.SignalDependencies] = None
) -> list:
    created_orders = []
    for asset in sorted(sellable_assets):
        try:
            new_orders = await convert_asset_to_target_asset(
                trading_mode, asset, target_asset, tickers, asset_amount=None, dependencies=dependencies
            )
            created_orders += new_orders
        except KeyError as err:
            trading_mode.logger.exception(
                err, True, f"Impossible to convert {asset} into {target_asset}: missing {err} market status"
            )
    return created_orders


async def convert_asset_to_target_asset(
    trading_mode, asset: str, target_asset: str, tickers: dict, asset_amount=None,
    dependencies: typing.Optional[commons_signals.SignalDependencies] = None
) -> list:
    if asset == target_asset:
        return []
    created_orders = []
    tickers = tickers or {}
    portfolio = trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio
    if asset in portfolio and portfolio[asset].available:
        created_orders.extend(
            await convert_with_market_or_limit_order(
                trading_mode, asset, target_asset, tickers, asset_amount, dependencies=dependencies
            )
        )
    return created_orders


async def convert_with_market_or_limit_order(
    trading_mode, asset: str, target_asset: str, tickers: dict, asset_amount=None,
    dependencies: typing.Optional[commons_signals.SignalDependencies] = None
) -> list:
    # get symbol of the order
    symbol, order_type = _get_associated_symbol_and_order_type(trading_mode, asset, target_asset)
    if symbol is None:
        # can't convert asset into target_asset
        trading_mode.logger.warning(
            f"Impossible to convert {asset} into {target_asset}: no associated trading pair "
            f"on {trading_mode.exchange_manager.exchange_name}"
        )
        return []

    # get symbol price
    price_base = asset
    price_target = target_asset
    if order_type is trading_enums.TraderOrderType.BUY_MARKET:
        price_base = target_asset
        price_target = asset

    price = trading_personal_data.get_asset_price_from_converter_or_tickers(
        trading_mode.exchange_manager, price_base, price_target, symbol, tickers
    )

    if not price:
        # can't get price, should not happen as symbol is in client_symbols
        trading_mode.logger.error(
            f"Impossible to convert {asset} into {target_asset}: {symbol} ticker can't be fetched"
        )
        return []

    if trading_personal_data.get_trade_order_type(order_type) is not trading_enums.TradeOrderType.MARKET:
        # can't use market orders: use limit orders with price a bit under the current price to instant fill it.
        price = get_instantly_filled_limit_order_adapted_price(price, order_type)

    # get order quantity
    quantity = _get_available_or_target_quantity(trading_mode, symbol, order_type, price, asset_amount)
    symbol_market = trading_mode.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
    created_orders = []
    for order_quantity, order_price in \
            trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
                quantity,
                price,
                symbol_market
            ):
        # create order
        order = trading_personal_data.create_order_instance(
            trader=trading_mode.exchange_manager.trader,
            order_type=order_type,
            symbol=symbol,
            current_price=price,
            quantity=order_quantity,
            price=order_price
        )
        initialized_order = await trading_mode.create_order(order, dependencies=dependencies)
        if isinstance(initialized_order, trading_personal_data.LimitOrder) and initialized_order.simulated:
            # on simulator, this order should be instantly filled now as its price is meant to be instantly filled
            await initialized_order.on_fill()
        created_orders.append(initialized_order)
    return created_orders


def get_instantly_filled_limit_order_adapted_price(
    price: decimal.Decimal, order_type: trading_enums.TraderOrderType
) -> decimal.Decimal:
    price_delta = price * constants.INSTANT_FILLED_LIMIT_ORDER_PRICE_DELTA
    if order_type is trading_enums.TraderOrderType.SELL_LIMIT:
        price -= price_delta
    elif order_type is trading_enums.TraderOrderType.BUY_LIMIT:
        price += price_delta
    else:
        logging.get_logger(__name__).error(
            f"Unhandled order type in convertor limit order price adapter: {order_type}"
        )
    return price


def get_instantly_filled_limit_order_adapted_price_and_quantity(
    price: decimal.Decimal, quantity: decimal.Decimal, order_type: trading_enums.TraderOrderType
) -> (decimal.Decimal, decimal.Decimal):
    adapted_price = get_instantly_filled_limit_order_adapted_price(price, order_type)
    origin_cost = price * quantity
    # keep the same total cost, adapt quantity
    adapted_quantity = origin_cost / adapted_price
    return adapted_price, adapted_quantity


def _get_associated_symbol_and_order_type(trading_mode, asset: str, target_asset: str) \
     -> (str, trading_enums.TraderOrderType):
    symbol, reversed_symbol = exchange_util.get_associated_symbol(trading_mode.exchange_manager, asset, target_asset)
    if symbol is None:
        return None, None
    order_type = trading_enums.TraderOrderType.BUY_MARKET if reversed_symbol else \
        trading_enums.TraderOrderType.SELL_MARKET
    if not trading_mode.exchange_manager.exchange.is_market_open_for_order_type(symbol, order_type):
        # can't use market orders: use limit orders instead
        order_type = trading_enums.TraderOrderType.BUY_LIMIT if order_type is trading_enums.TraderOrderType.BUY_MARKET \
            else trading_enums.TraderOrderType.SELL_LIMIT
        if not trading_mode.exchange_manager.exchange.is_market_open_for_order_type(symbol, order_type):
            # can't convert asset: still try with limit orders but it will probably fail
            trading_mode.logger.error(
                f"Both market and {order_type} order are currently unsupported. Trying limit orders anyway."
            )
    return symbol, order_type


def _get_available_or_target_quantity(trading_mode, symbol, order_type, price, asset_amount) -> decimal.Decimal:
    side = (
        trading_enums.TradeOrderSide.SELL
        if order_type in (trading_enums.TraderOrderType.SELL_MARKET, trading_enums.TraderOrderType.SELL_LIMIT)
        else trading_enums.TradeOrderSide.BUY
    )

    currency_available, _, market_quantity = trading_personal_data.get_portfolio_amounts(
        trading_mode.exchange_manager, symbol, price, portfolio_type=common_constants.PORTFOLIO_AVAILABLE
    )
    if asset_amount is None:
        quantity = currency_available if side is trading_enums.TradeOrderSide.SELL else market_quantity
    else:
        try:
            quantity = asset_amount if side is trading_enums.TradeOrderSide.SELL else (asset_amount / price)
        except (decimal.DivisionByZero, decimal.InvalidOperation):
            quantity = constants.ZERO

    adapted_quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
        trading_mode.exchange_manager, symbol, order_type, quantity, price, side
    )
    return adapted_quantity


async def notify_portfolio_optimization_complete():
    try:
        import octobot_services.api as services_api
        import octobot_services.enums as services_enum
        title = "Portfolio optimization complete"
        alert_content = "Your portfolio funds are now in a optimal configuration to start your strategy"
        await services_api.send_notification(services_api.create_notification(
            alert_content,
            title=title,
            markdown_text=alert_content,
            category=services_enum.NotificationCategory.TRADES)
        )
    except ImportError as e:
        logging.get_logger(__name__).exception(e, True, f"Impossible to send notification: {e}")


def get_trading_modes_of_this_type_on_this_matrix(trading_mode) -> list:
    import octobot_trading.api  # avoid circular import issues
    other_trading_modes = []
    for exchange_id in octobot_trading.api.get_all_exchange_ids_with_same_matrix_id(
        trading_mode.exchange_manager.exchange_name, trading_mode.exchange_manager.id
    ):
        exchange_manager = octobot_trading.api.get_exchange_manager_from_exchange_id(exchange_id)
        other_trading_modes.extend(
            other_trading_mode
            for other_trading_mode in exchange_manager.trading_modes
            if isinstance(other_trading_mode, type(trading_mode))
        )
    return other_trading_modes


def enabled_trader_only(raise_when_disabled=False, disabled_return_value=None):
    # inner level to allow passing params to the decorator
    def inner_enabled_trader_only(func):
        async def enabled_trader_only_wrapper(self, *args, **kwargs):
            if self.exchange_manager.trader.is_enabled:
                return await func(self, *args, **kwargs)
            message = (
                f"Trading on {self.exchange_manager.exchange_name} has been paused, "
                f"skipping {self.__class__.__name__} execution"
            )
            if raise_when_disabled:
                raise errors.TraderDisabledError(message)
            self.logger.warning(message)
            return disabled_return_value
        return enabled_trader_only_wrapper
    return inner_enabled_trader_only
