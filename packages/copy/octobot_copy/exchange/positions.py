import decimal
import typing

import octobot_commons.signals as commons_signals
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.modes as trading_modes
import octobot_trading.personal_data as trading_personal_data

import octobot_copy.exchange.market as exchange_market
import octobot_copy.exchange.orders as exchange_orders

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges


class PositionsInterface:
    def __init__(
        self,
        exchange_manager: "octobot_trading.exchanges.ExchangeManager",
        orders: "exchange_orders.OrdersInterface",
        market: "exchange_market.MarketInterface",
    ):
        self._exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager
        self._orders: exchange_orders.OrdersInterface = orders
        self._market: exchange_market.MarketInterface = market

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
                await self._orders.cancel_symbol_open_orders(symbol, dependencies=dependencies)
                return []

        # Cancel open close-side orders BEFORE computing effective position size so that a stuck
        # IOC→GTC order from a previous cycle does not subtract from pending_open_quantity and wrongly suppress the fresh close order.
        close_side = (
            trading_enums.TradeOrderSide.BUY if position.is_short()
            else trading_enums.TradeOrderSide.SELL
        )
        await self._orders.cancel_symbol_open_orders(symbol, dependencies, allowed_sides={close_side})
        pending_open_quantity = self._orders.get_pending_open_quantity(symbol)
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
            if self._market.is_market_open_for_order_type(symbol, ideal_order_type)
            else (
                trading_enums.TraderOrderType.SELL_LIMIT
                if side is trading_enums.TradeOrderSide.SELL
                else trading_enums.TraderOrderType.BUY_LIMIT
            )
        )

        quantity = self._orders.adapt_order_quantity_because_fees(
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
            created_order = await self._orders.create_order(
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
