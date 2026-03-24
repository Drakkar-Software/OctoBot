import asyncio
import decimal
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.logging as commons_logging
import octobot_commons.signals as commons_signals
import octobot_trading.api as trading_api
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_trading.modes as trading_modes
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.personal_data.orders.order_util as order_util
import octobot_trading.signals.signal_creation as signal_creation

import octobot_copy.constants as copy_constants
import octobot_copy.exchange.exchange_public_data as exchange_public_data

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class ExchangePrivateData:
    def __init__(
        self,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        trading_mode: typing.Optional["trading_modes.AbstractTradingMode"],
        public_data: exchange_public_data.ExchangePublicData,
    ):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager
        self._trading_mode: typing.Optional["trading_modes.AbstractTradingMode"] = trading_mode
        self._public_data: exchange_public_data.ExchangePublicData = public_data

    def get_symbol_position(
        self,
        symbol: str,
        side: trading_enums.PositionSide = trading_enums.PositionSide.BOTH,
    ):
        return self._exchange_manager.exchange_personal_data.positions_manager.get_symbol_position(
            symbol, side
        )

    async def refresh_real_trader_position(self, position, *, force_job_execution: bool = True) -> None:
        await self._exchange_manager.exchange_personal_data.positions_manager.refresh_real_trader_position(
            position, force_job_execution=force_job_execution
        )

    async def create_order(
        self,
        order_type: trading_enums.TraderOrderType,
        symbol: str,
        current_price: decimal.Decimal,
        quantity: decimal.Decimal,
        price: decimal.Decimal,
        *,
        reduce_only: typing.Optional[bool] = None,
        close_position: bool = False,
        params: typing.Optional[dict] = None,
        wait_for_creation=True,
        creation_timeout=trading_constants.INDIVIDUAL_ORDER_SYNC_TIMEOUT,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
    ):
        order = trading_personal_data.create_order_instance(
            trader=self._exchange_manager.trader,
            order_type=order_type,
            symbol=symbol,
            current_price=current_price,
            quantity=quantity,
            price=price,
            reduce_only=reduce_only,
            close_position=close_position,
        )
        if self._trading_mode is not None:
            return await self._trading_mode.create_order(
                order,
                loaded=False,
                params=params,
                wait_for_creation=wait_for_creation,
                creation_timeout=creation_timeout,
                dependencies=dependencies,
            )
        return await self._exchange_manager.trader.create_order(
            order,
            loaded=False,
            params=params,
            wait_for_creation=wait_for_creation,
            creation_timeout=creation_timeout,
            force_if_disabled=False  # type: ignore
        )

    async def create_orders(
        self,
        order_type: trading_enums.TraderOrderType,
        symbol: str,
        current_price: decimal.Decimal,
        quantity: decimal.Decimal,
        order_target_price: decimal.Decimal,
        symbol_market,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
        *,
        reduce_only: typing.Optional[bool] = None,
        close_position: bool = False,
        skip_none_create_results: bool = False,
    ) -> tuple[list, bool]:
        created_orders: list = []
        orders_should_have_been_created = False
        adapted_target_price = order_target_price
        side = trading_enums.TradeOrderSide.BUY if order_type in (
            trading_enums.TraderOrderType.BUY_MARKET, trading_enums.TraderOrderType.BUY_LIMIT
        ) else trading_enums.TradeOrderSide.SELL
        adapted_quantity = trading_personal_data.decimal_adapt_order_quantity_because_fees(
            self._exchange_manager, symbol, order_type, quantity, order_target_price, side
        )
        if trading_personal_data.get_trade_order_type(order_type) is not trading_enums.TradeOrderType.MARKET:
            adapted_target_price, adapted_quantity = (
                trading_modes.get_instantly_filled_limit_order_adapted_price_and_quantity(
                    adapted_target_price, adapted_quantity, order_type
                )
            )
        for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            adapted_quantity,
            adapted_target_price,
            symbol_market,
        ):
            orders_should_have_been_created = True
            created_order = await self.create_order(
                order_type,
                symbol,
                current_price,
                order_quantity,
                order_price,
                reduce_only=reduce_only,
                close_position=close_position,
                dependencies=dependencies,
            )
            if skip_none_create_results:
                if created_order is not None:
                    created_orders.append(created_order)
            else:
                created_orders.append(created_order)
        return created_orders, orders_should_have_been_created

    async def wait_for_orders_to_fill(self, orders: list) -> None:
        if orders:
            await asyncio.gather(
                *[
                    trading_personal_data.wait_for_order_fill(
                        order, copy_constants.FILL_ORDER_TIMEOUT, True
                    )
                    for order in orders
                ],
                return_exceptions=True,
            )

    def get_open_orders(self, symbol: typing.Optional[str] = None, active: typing.Optional[bool] = None) -> list:
        return trading_api.get_open_orders(self._exchange_manager, symbol=symbol, active=active)

    def get_pending_open_quantity(self, symbol: str) -> decimal.Decimal:
        pending_quantity = decimal.Decimal(0)
        for order in self.get_open_orders(symbol=symbol):
            remaining_quantity = order.origin_quantity - order.filled_quantity
            if remaining_quantity <= decimal.Decimal(0):
                continue
            if order.side is trading_enums.TradeOrderSide.BUY:
                pending_quantity += remaining_quantity
            elif order.side is trading_enums.TradeOrderSide.SELL:
                pending_quantity -= remaining_quantity
        return pending_quantity

    async def get_pre_order_data(
        self,
        symbol: str,
        timeout: typing.Optional[int] = trading_constants.ORDER_DATA_FETCHING_TIMEOUT,
        portfolio_type=commons_constants.PORTFOLIO_AVAILABLE,
        target_price=None,
    ):
        return await trading_personal_data.get_pre_order_data(
            self._exchange_manager,
            symbol=symbol,
            timeout=timeout,
            portfolio_type=portfolio_type,
            target_price=target_price,
        )

    def get_futures_max_order_size(
        self,
        symbol: str,
        side: trading_enums.TradeOrderSide,
        current_price: decimal.Decimal,
        reduce_only: bool,
        current_symbol_holding: decimal.Decimal,
        market_quantity: decimal.Decimal,
    ) -> tuple[decimal.Decimal, bool]:
        return order_util.get_futures_max_order_size(
            self._exchange_manager,
            symbol,
            side,
            current_price,
            reduce_only,
            current_symbol_holding,
            market_quantity,
        )

    async def convert_assets_to_target_asset(
        self,
        sellable_assets: list,
        target_asset: str,
        tickers: dict,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
    ) -> list:
        if self._trading_mode is None:
            raise ValueError("ExchangePrivateData.convert_assets_to_target_asset requires trading_mode")
        return await modes_util.convert_assets_to_target_asset(
            self._trading_mode,
            sellable_assets,
            target_asset,
            tickers,
            dependencies=dependencies,
        )

    async def cancel_order(
        self,
        order,
        ignored_order: object = None,
        wait_for_cancelling: bool = True,
        dependencies: typing.Optional[commons_signals.SignalDependencies] = None,
    ) -> tuple[bool, commons_signals.SignalDependencies]:
        if self._trading_mode is not None:
            return await self._trading_mode.cancel_order(
                order,
                ignored_order=ignored_order,
                wait_for_cancelling=wait_for_cancelling,
                dependencies=dependencies,
            )
        return await signal_creation.cancel_order(
            self._exchange_manager,
            False,
            order,
            ignored_order=ignored_order,
            wait_for_cancelling=wait_for_cancelling,
            dependencies=dependencies,
        )

    async def cancel_symbol_open_orders(
        self,
        symbol: str,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        allowed_sides: typing.Optional[set[trading_enums.TradeOrderSide]] = None,
    ) -> typing.Optional[commons_signals.SignalDependencies]:
        cancelled_dependencies = commons_signals.SignalDependencies()
        for order in self.get_open_orders(symbol=symbol):
            if isinstance(order, trading_personal_data.MarketOrder):
                continue
            if allowed_sides and order.side not in allowed_sides:
                continue
            try:
                is_cancelled, dependency = await self.cancel_order(order)
                if is_cancelled and dependency is not None:
                    cancelled_dependencies.extend(dependency)
            except trading_errors.UnexpectedExchangeSideOrderStateError as err:
                commons_logging.get_logger(self.__class__.__name__).warning(
                    f"Skipped order cancel: {err}, order: {order}"
                )
        if dependencies is not None:
            dependencies.extend(cancelled_dependencies)
        return cancelled_dependencies or None

    def adapt_order_quantity_because_fees(
        self,
        symbol: str,
        order_type: trading_enums.TraderOrderType,
        quantity: decimal.Decimal,
        price: decimal.Decimal,
        side: trading_enums.TradeOrderSide,
    ) -> decimal.Decimal:
        return trading_personal_data.decimal_adapt_order_quantity_because_fees(
            self._exchange_manager, symbol, order_type, quantity, price, side
        )

    def check_and_adapt_order_details_if_necessary(
        self,
        symbol: str,
        quantity: decimal.Decimal,
        price: decimal.Decimal,
    ) -> tuple[decimal.Decimal, dict]:
        symbol_market = self._exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
        adapted_quantity = trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            quantity,
            price,
            symbol_market,
        )
        return adapted_quantity, symbol_market

    def get_traded_assets_holdings_value(
        self,
        unit: str,
        coins_whitelist: typing.Optional[typing.Iterable] = None,
    ) -> decimal.Decimal:
        portfolio_manager = self._exchange_manager.exchange_personal_data.portfolio_manager
        return portfolio_manager.portfolio_value_holder.get_traded_assets_holdings_value(
            unit, coins_whitelist
        )

    def get_free_reference_market_holding(self, reference_market: str) -> decimal.Decimal:
        portfolio_manager = self._exchange_manager.exchange_personal_data.portfolio_manager
        return portfolio_manager.portfolio.get_currency_portfolio(reference_market).available

    async def close_symbol_position(
        self,
        symbol: str,
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        current_price: decimal.Decimal,
        symbol_market,
        desired_futures_position_size: typing.Optional[decimal.Decimal] = None,
    ) -> list:
        position = self.get_symbol_position(symbol, trading_enums.PositionSide.BOTH)
        if position.is_idle():
            # Force a refresh from the exchange before concluding there is nothing to sell.
            await self.refresh_real_trader_position(position, force_job_execution=True)
            position = self.get_symbol_position(symbol, trading_enums.PositionSide.BOTH)
            if position.is_idle():
                await self.cancel_symbol_open_orders(symbol, dependencies=dependencies)
                return []

        # Cancel open close-side orders BEFORE computing effective position size so that a stuck
        # IOC→GTC order from a previous cycle does not subtract from pending_open_quantity and wrongly suppress the fresh close order.
        close_side = (
            trading_enums.TradeOrderSide.BUY if position.is_short()
            else trading_enums.TradeOrderSide.SELL
        )
        await self.cancel_symbol_open_orders(symbol, dependencies, allowed_sides={close_side})
        pending_open_quantity = self.get_pending_open_quantity(symbol)
        position_size = decimal.Decimal(str(position.size))
        if position.is_short():
            effective_position_size = -abs(position_size) + pending_open_quantity
        else:
            effective_position_size = abs(position_size) + pending_open_quantity

        if effective_position_size == trading_constants.ZERO:
            return []

        if effective_position_size > trading_constants.ZERO:
            side = trading_enums.TradeOrderSide.SELL
        else:
            side = trading_enums.TradeOrderSide.BUY

        quantity_to_close = abs(effective_position_size)
        if desired_futures_position_size is not None and effective_position_size > trading_constants.ZERO:
            quantity_to_close = max(
                trading_constants.ZERO,
                effective_position_size - desired_futures_position_size,
            )
        if quantity_to_close <= trading_constants.ZERO:
            return []

        ideal_order_type = (
            trading_enums.TraderOrderType.SELL_MARKET
            if side is trading_enums.TradeOrderSide.SELL
            else trading_enums.TraderOrderType.BUY_MARKET
        )
        order_type = (
            ideal_order_type
            if self._public_data.is_market_open_for_order_type(symbol, ideal_order_type)
            else (
                trading_enums.TraderOrderType.SELL_LIMIT
                if side is trading_enums.TradeOrderSide.SELL
                else trading_enums.TraderOrderType.BUY_LIMIT
            )
        )

        quantity = self.adapt_order_quantity_because_fees(
            symbol, order_type, quantity_to_close, current_price, side
        )
        if trading_personal_data.get_trade_order_type(order_type) is not trading_enums.TradeOrderType.MARKET:
            current_price, quantity = trading_modes.get_instantly_filled_limit_order_adapted_price_and_quantity(
                current_price, quantity, order_type
            )

        created_orders = []
        for order_quantity, order_price in trading_personal_data.decimal_check_and_adapt_order_details_if_necessary(
            quantity,
            current_price,
            symbol_market,
        ):
            created_order = await self.create_order(
                order_type,
                symbol,
                order_price,
                order_quantity,
                order_price,
                reduce_only=True,
                close_position=True,
                dependencies=dependencies,
            )
            if created_order is not None:
                created_orders.append(created_order)

        return created_orders
