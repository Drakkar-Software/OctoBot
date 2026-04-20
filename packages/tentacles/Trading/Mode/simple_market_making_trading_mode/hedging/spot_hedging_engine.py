import decimal
import typing

import octobot_trading.constants as trading_constants
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums
import octobot_trading.personal_data as personal_data
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.hedging_engine as hedging_engine
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors


# switch to stop loss if the edging order is not filled after this timeout
DEFAULT_ACTIVE_ORDER_SWAP_TIMEOUT = 60


class SpotHedgingEngine(hedging_engine.HedgingEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active_order_swap_timeout = DEFAULT_ACTIVE_ORDER_SWAP_TIMEOUT

    def _get_base_and_quote_hedging_budget(self, details: hedging_engine.SymbolHedgingDetails) -> tuple[decimal.Decimal, decimal.Decimal]:
        base_available_holding = trading_api.get_portfolio_currency(self._hedging_exchange_manager, details.symbol.base).available
        quote_available_holding = trading_api.get_portfolio_currency(self._hedging_exchange_manager, details.symbol.quote).available
        return base_available_holding, quote_available_holding

    async def _create_hedging_order(self, fill: hedging_engine.HedgingFill) -> personal_data.Order:
        details = self.get_symbol_details(fill.fill_trade.symbol)
        hedging_limit_price = fill.hedging_price
        heding_side = (
            trading_enums.TradeOrderSide.SELL if fill.fill_trade.side is trading_enums.TradeOrderSide.BUY
            else trading_enums.TradeOrderSide.BUY
        )
        if details.hedging_max_loss_threshold == 0:
            stop_price = None
        else:
            stop_price = hedging_limit_price * (1 + (
                details.hedging_max_loss_threshold * 
                (1 if heding_side is trading_enums.TradeOrderSide.BUY else -1)
            ) / trading_constants.ONE_HUNDRED)
        if hedging_order := await self._create_maybe_oco_hedging_order(
            fill.fill_trade.symbol,
            heding_side,
            fill.fill_trade.executed_quantity,
            hedging_limit_price,
            stop_price
        ):
            return hedging_order
        raise hedging_errors.HedgingOrderCreationError(
            f"Failed to create hedging order for {fill.fill_trade.symbol}. "
            f"Hedging limit price: {hedging_limit_price}, "
            f"Hedging side: {heding_side}, "
            f"Stop price: {stop_price}"
        )

    async def _create_maybe_oco_hedging_order(
        self,
        symbol: str,
        heding_side: trading_enums.TradeOrderSide,
        locally_filled_amount: decimal.Decimal,
        hedging_limit_price: decimal.Decimal,
        stop_price: typing.Optional[decimal.Decimal],
    ) -> typing.Optional[personal_data.Order]:
        symbol_market = self._hedging_exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
        oco_group = None
        if stop_price is not None:
            # stop price is set, enable OCO hedging order
            if not self._hedging_exchange_manager.trader.enable_inactive_orders:
                raise hedging_errors.InactiveOrdersNotEnabledError(
                    f"Inactive orders are not enabled for {self._hedging_exchange_manager.exchange_name}. "
                    f"Cannot create OCO hedging order."
                )
            # create ideal hedging order first and if not filled after timeout, switch to stop loss
            active_order_swap_strategy = personal_data.TakeProfitFirstActiveOrderSwapStrategy(
                swap_timeout=self._active_order_swap_timeout,
            )
            oco_group = self._hedging_exchange_manager.exchange_personal_data.orders_manager.create_group(
                personal_data.OneCancelsTheOtherOrderGroup, active_order_swap_strategy=active_order_swap_strategy
            )

        hedging_order_type = (
            trading_enums.TraderOrderType.BUY_LIMIT
            if heding_side is trading_enums.TradeOrderSide.BUY
            else trading_enums.TraderOrderType.SELL_LIMIT
        )
        hedging_orders = []
        for order_quantity, order_price in personal_data.decimal_check_and_adapt_order_details_if_necessary(
            locally_filled_amount,
            hedging_limit_price,
            symbol_market
        ):
            hedging_orders.append(personal_data.create_order_instance(
                trader=self._hedging_exchange_manager.trader,
                order_type=hedging_order_type,
                symbol=symbol,
                current_price=hedging_limit_price,
                quantity=order_quantity,
                price=order_price,
                group=oco_group,
            ))

        potential_err = self.get_failed_to_create_hedging_order_error(
            symbol, locally_filled_amount, hedging_limit_price, stop_price
        )
        if len(hedging_orders) < 1:
            raise hedging_errors.TooSmallHedgingOrderError(potential_err)
        if len(hedging_orders) > 1:
            raise hedging_errors.TooLargeHedgingOrderError(potential_err)

        hedging_order = hedging_orders[0]
        if stop_price is None:
            self._logger.info(f"Creating hedging limit order (no stop): {str(hedging_order)}")
            return await self._hedging_exchange_manager.trader.create_order(
                hedging_order, wait_for_creation=False
            )

        stop_orders = []
        for order_quantity, order_price in personal_data.decimal_check_and_adapt_order_details_if_necessary(
            locally_filled_amount,
            stop_price,
            symbol_market
        ):
            stop_orders.append(personal_data.create_order_instance(
                trader=self._hedging_exchange_manager.trader,
                order_type=trading_enums.TraderOrderType.STOP_LOSS,
                symbol=symbol,
                current_price=hedging_limit_price,
                quantity=order_quantity,
                price=order_price,
                side=heding_side,
                group=oco_group,
            ))
        if len(stop_orders) < 1:
            raise hedging_errors.TooSmallHedgingOrderError(potential_err)
        if len(stop_orders) > 1:
            raise hedging_errors.TooLargeHedgingOrderError(potential_err)
        stop_order = stop_orders[0]
        trigger_above_by_order_id = {
            # hedging buy limit order should trigger when price is <= the limit price
            hedging_order.order_id: not heding_side is trading_enums.TradeOrderSide.BUY,
            # stop loss buy order should trigger when price is >= the stop price
            stop_order.order_id: heding_side is trading_enums.TradeOrderSide.BUY,
        }
        stop_prefix = "inactive"
        if stop_order.is_self_managed():
            stop_prefix = "self-managed"
        else:
            await oco_group.active_order_swap_strategy.apply_inactive_orders(
                [hedging_order, stop_order],
                trigger_above_by_order_id
            )
        self._logger.info(f"Creating hedging {stop_prefix} stop order: {str(stop_order)}")
        stop_order = await self._hedging_exchange_manager.trader.create_order(
            stop_order, wait_for_creation=False
        )
        self._logger.info(f"Creating hedging order: {str(hedging_order)}")
        return await self._hedging_exchange_manager.trader.create_order(
            hedging_order, wait_for_creation=False
        )

    def get_failed_to_create_hedging_order_error(
        self,
        symbol: str,
        locally_filled_amount: decimal.Decimal,
        hedging_limit_price: decimal.Decimal,
        stop_price: typing.Optional[decimal.Decimal],
    ) -> str:
        stop_cost = (
            str(locally_filled_amount * stop_price) if stop_price is not None else "n/a (limit only)"
        )
        return (
            f"Failed to create [{self._hedging_exchange_manager.exchange_name}] hedging {symbol} order for a quantity of {locally_filled_amount} "
            f"(order costs: arbitrage {locally_filled_amount*hedging_limit_price}, stop {stop_cost})"
        )
