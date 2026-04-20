import decimal
import typing
import asyncio
import time
import enum
import dataclasses

import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.symbols as symbols_util
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.enums as trading_enums
import octobot_trading.exchange_channel as exchanges_channel
import octobot_trading.constants as trading_constants
import octobot_trading.api as trading_api
import octobot_trading.util as trading_util
import octobot_trading.personal_data as personal_data
import tentacles.Trading.Mode.simple_market_making_trading_mode.advanced_order_book_distribution as advanced_order_book_distribution
import tentacles.Trading.Mode.simple_market_making_trading_mode.hedging.errors as hedging_errors
import tentacles.Automation.trigger_events.volatility_threshold_event.volatility_threshold as volatility_threshold_event


class HedgingEngineState(enum.Enum):
    PENDING_START = "pending_start"
    INITIALIZATION_FAILED = "initialization_failed"
    MISSING_HEDGING_FUNDS = "missing_hedging_funds"
    HEDGING = "hedging"
    MAX_VOLATILITY_REACHED = "max_volatility_reached"
    STOPPED = "stopped"


BALANCE_INITIALIZATION_TIMEOUT = 20


@dataclasses.dataclass
class HedgingFill:
    fill_trade: personal_data.Trade
    hedging_price: decimal.Decimal
    is_locked: bool = True
    hedging_order: typing.Optional[personal_data.Order] = None

    def __repr__(self):
        return (
            f"HedgingFill(fill_trade={self.fill_trade.to_dict()}, hedging_price={self.hedging_price}, "
            f"is_locked={self.is_locked}, hedging_order={self.hedging_order.to_dict() if self.hedging_order else None})"
        )

    def get_locked_base_and_quote(self) -> tuple[decimal.Decimal, decimal.Decimal]:
        if self.is_locked:
            if self.fill_trade.side is trading_enums.TradeOrderSide.BUY:
                # filled a buy order: locked acquired base
                return self.fill_trade.executed_quantity, trading_constants.ZERO
            else:
                # filled a sell order: locked acquired quote
                return trading_constants.ZERO, self.fill_trade.executed_quantity * self.fill_trade.executed_price
        return trading_constants.ZERO, trading_constants.ZERO

    def get_hedging_order_fee(self, hedging_exchange_manager: trading_exchanges.ExchangeManager, filled_hedging_order: dict) -> tuple[dict, bool]:
        is_estimated_hedging_fee = False
        hedging_fee = filled_hedging_order.get(trading_enums.ExchangeConstantsOrderColumns.FEE.value, {})
        hedging_price = decimal.Decimal(str(filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]))
        if not hedging_fee.get(trading_enums.FeePropertyColumns.IS_FROM_EXCHANGE.value, False):
            hedging_order_type = trading_enums.TraderOrderType.SELL_MARKET if self.fill_trade.side is trading_enums.TradeOrderSide.BUY else trading_enums.TraderOrderType.BUY_MARKET
            hedging_fee = hedging_exchange_manager.exchange.get_trade_fee(
                self.fill_trade.symbol, hedging_order_type, self.fill_trade.executed_quantity, hedging_price, trading_enums.ExchangeConstantsOrderColumns.TAKER.value
            )
            is_estimated_hedging_fee = True
        return hedging_fee, is_estimated_hedging_fee

    def get_quote_valued_fees(
        self,
        filled_hedging_order: dict,
        hedging_exchange_manager: trading_exchanges.ExchangeManager,
    ) -> (decimal.Decimal, str):
        # hedging order fees
        base, quote = symbols_util.parse_symbol(self.fill_trade.symbol).base_and_quote()
        hedging_fee, is_estimated_hedging_fee = self.get_hedging_order_fee(hedging_exchange_manager, filled_hedging_order)
        hedging_price = decimal.Decimal(str(filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]))
        hedging_base_fee_in_quote = decimal.Decimal(str(personal_data.get_fees_for_currency(hedging_fee, base))) * hedging_price
        hedging_quote_fee = decimal.Decimal(str(personal_data.get_fees_for_currency(hedging_fee, quote)))

        # trading order fees
        trading_fee, is_estimated_trading_fee = personal_data.get_real_or_estimated_trade_fee(self.fill_trade)
        trading_base_fee_in_quote = decimal.Decimal(str(personal_data.get_fees_for_currency(trading_fee, base))) * self.fill_trade.executed_price
        trading_quote_fee = decimal.Decimal(str(personal_data.get_fees_for_currency(trading_fee, quote)))

        total_quote_fees = hedging_base_fee_in_quote + hedging_quote_fee + trading_base_fee_in_quote + trading_quote_fee
        fees_summary = (
            f"Total: {total_quote_fees} {quote} ("
            f"trading: {self._get_fees_summary(trading_fee, self.fill_trade.executed_price, is_estimated_trading_fee)}, "
            f"hedging: {self._get_fees_summary(hedging_fee, hedging_price, is_estimated_hedging_fee)})"
        )
        return total_quote_fees, fees_summary
    
    def _get_fees_summary(self, fee: dict, filled_price: decimal.Decimal, is_estimated: bool) -> str:
        fee_cost = fee[trading_enums.FeePropertyColumns.COST.value]
        quote = symbols_util.parse_symbol(self.fill_trade.symbol).quote
        current_currency = fee[trading_enums.FeePropertyColumns.CURRENCY.value]
        if current_currency != quote:
            quote_cost = fee_cost * filled_price 
            quote_cost_eq = f" (= {quote_cost} {quote})"
        else:
            quote_cost_eq = ""
        return f"{fee_cost} {current_currency}{quote_cost_eq} [{'estimated' if is_estimated else 'confirmed'}]"

    def get_summary(
        self,
        filled_hedging_order: dict,
        hedging_exchange_manager: trading_exchanges.ExchangeManager,
        trading_exchange_manager: trading_exchanges.ExchangeManager,
    ) -> str:
        base, quote = symbols_util.parse_symbol(self.fill_trade.symbol).base_and_quote()
        hedged_amount = decimal.Decimal(str(filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]))
        hedged_amount_details = ""
        if hedged_amount < self.fill_trade.executed_quantity:
            logging.get_logger(self.__class__.__name__).warning(
                f"{self.fill_trade.symbol}: hedged amount {hedged_amount} is {self.fill_trade.executed_quantity - hedged_amount} "
                f"less than locally filled amount {self.fill_trade.executed_quantity} "
                f"for [{hedging_exchange_manager.exchange_name}] order {self.fill_trade.exchange_order_id}. This might be due to different order precision."
            )
            hedged_amount_details = f" (used hedged amount {hedged_amount})"
        trading_total = hedged_amount * self.fill_trade.executed_price
        hedged_total = hedged_amount * decimal.Decimal(str(filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]))
        total_quote_fees, fees_summary = self.get_quote_valued_fees(
            filled_hedging_order, hedging_exchange_manager
        )
        profits = (
            hedged_total - trading_total # buy order on trading, sell on hedging: total sold should be > total bought
            if self.fill_trade.side is trading_enums.TradeOrderSide.BUY 
            else trading_total - hedged_total # sell order on trading, buy on hedging: total sold should be < total bought
        ) - total_quote_fees
        exec_details = ""
        if filled_hedging_order.get(
            trading_enums.ExchangeConstantsOrderColumns.TYPE.value, trading_enums.TradeOrderType.LIMIT.value
        ) != trading_enums.TradeOrderType.LIMIT.value:
            exec_details = "[Stop triggered] "
        return (
            f"Profits: {'+' if profits >= trading_constants.ZERO else ''}{profits} {quote} {exec_details}for "
            f"{self.fill_trade.side.value} {self.fill_trade.executed_quantity}{hedged_amount_details} {self.fill_trade.symbol} at {self.fill_trade.executed_price} (total: {trading_total} {quote}) [{trading_exchange_manager.exchange_name}] "
            f"hedged with {filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.SIDE.value]} "
            f"{filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value]} {base} "
            f"at {filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value]} "
            f"(total: {hedged_total} {quote}) [{hedging_exchange_manager.exchange_name}]. Fees: {fees_summary} "
            f"[{trading_exchange_manager.exchange_name}] order exchange id: {self.fill_trade.exchange_order_id}. "
        )

@dataclasses.dataclass
class SymbolHedgingDetails:
    symbol: symbols_util.Symbol
    # trading should be halted if the state is not "hedging"
    state: HedgingEngineState
    # set when the hedging engine has completed its initialization, doesn't mean it's healthy
    hedging_profit_threshold: decimal.Decimal
    hedging_max_loss_threshold: decimal.Decimal
    last_hedging_price: decimal.Decimal
    completed_initialization: asyncio.Event
    order_book_distribution: advanced_order_book_distribution.AdvancedOrderBookDistribution
    volatility_threshold_checker: volatility_threshold_event.VolatilityThresholdChecker
    hedging_fills_by_order_id: dict[str, list[HedgingFill]] = dataclasses.field(default_factory=dict)
    aborted_hedging_fills_by_order_id: dict[str, list[HedgingFill]] = dataclasses.field(default_factory=dict)


    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.hedging_profit_threshold >= (
            self.order_book_distribution.min_spread / decimal.Decimal("2") * trading_constants.ONE_HUNDRED
        ):
            raise hedging_errors.HedgingProfitThresholdTooHighError(
                f"{self.symbol}: Hedging profit threshold {self.hedging_profit_threshold} must be inferior to half of the minimum spread (min spread = {self.order_book_distribution.min_spread * trading_constants.ONE_HUNDRED})"
            )

    def stop(self):
        self.state = HedgingEngineState.STOPPED
        self.hedging_fills_by_order_id.clear()


class HedgingEngine:
    def __init__(
        self,
        trading_exchange_manager: trading_exchanges.ExchangeManager,
        hedging_exchange_name: str,
    ):
        self.hedging_exchange_name: str = hedging_exchange_name
        self._trading_exchange_manager: trading_exchanges.ExchangeManager = trading_exchange_manager
        self._hedging_exchange_manager: trading_exchanges.ExchangeManager = None # type: ignore
        self._consumers: list[exchanges_channel.ExchangeChannelConsumer] = []

        self._hedging_details_by_symbol: dict[str, SymbolHedgingDetails] = {}

        self._start_tasks: list[asyncio.Task] = []
        self._logger = logging.get_logger(
            f"{self.__class__.__name__}[{self._trading_exchange_manager.exchange_name}]"
        )

    def register_symbol(
        self, 
        symbol: str,
        hedging_profit_threshold: decimal.Decimal,
        hedging_max_loss_threshold: decimal.Decimal,
        order_book_distribution: advanced_order_book_distribution.AdvancedOrderBookDistribution,
        max_positive_percent_price_change: float,
        max_negative_percent_price_change: float,
        average_price_counted_minutes: int,
    ):
        self._hedging_details_by_symbol[symbol] = SymbolHedgingDetails(
            symbol=symbols_util.parse_symbol(symbol),
            state=HedgingEngineState.PENDING_START,
            hedging_profit_threshold=hedging_profit_threshold,
            hedging_max_loss_threshold=hedging_max_loss_threshold,
            completed_initialization=asyncio.Event(),
            order_book_distribution=order_book_distribution,
            last_hedging_price=trading_constants.ZERO,
            volatility_threshold_checker=volatility_threshold_event.VolatilityThresholdChecker(
                symbol=symbol,
                period_in_minutes=average_price_counted_minutes,
                max_allowed_positive_percentage_change=decimal.Decimal(str(max_positive_percent_price_change)),
                max_allowed_negative_percentage_change=decimal.Decimal(str(max_negative_percent_price_change)),
            ),
        )
        self._start_tasks.append(
            asyncio.create_task(self._async_start_for_hedging_details(self._hedging_details_by_symbol[symbol]))
        )


    async def hedge_filled_or_partially_filled_order(self, order: dict):
        # 1. lock funds on trading exchange for the newly acquired amount
        try:
            new_fill = self._register_hedging_fill(order)
        except hedging_errors.HedgingAlreadyCountedFillAmountError as err:
            if order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.CANCELED.value:
                # order was partially filled, then canceled: no need to register a fill, this can happen and is normal
                self._logger.debug(
                    f"Skipped registering hedging new fill for partially filled and now canceled order "
                    f"[{order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}]: order fill is already counted."
                )
            else:
                # not normal: raise error
                raise
        # 2. create mirror order on hedging exchange
        try:
            new_fill.hedging_order = await self._create_hedging_order(new_fill)
        except (hedging_errors.TooSmallHedgingOrderError, hedging_errors.TooLargeHedgingOrderError) as err:
            if order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] < order[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] and isinstance(err, hedging_errors.TooSmallHedgingOrderError):
                # order is partially filled, more will come: include the rest in the next fill
                self._logger.warning(
                    f"Skipped creating hedging order for order [{order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}]: {err} ({err.__class__.__name__})"
                )
            else:
                self._logger.exception(
                    err, 
                    True, 
                    f"Failed to create hedging order for filled order [{order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}]: {err} ({err.__class__.__name__})"
                )
            self._abort_hedging_fill(new_fill)
            
        # 3. funds will automatically be unlocked when the hedging order is filled

    async def _create_hedging_order(self, fill: HedgingFill) -> personal_data.Order:
        raise NotImplementedError("_create_hedging_order is not implemented")

    def _on_hedging_order_filled(self, filled_hedging_order: dict):
        if fill := self._get_order_associated_hedging_fill(filled_hedging_order):
            locked_base, locked_quote = fill.get_locked_base_and_quote()
            base, quote = symbols_util.parse_symbol(fill.fill_trade.symbol).base_and_quote()
            self._logger.info(
                f"Hedging order [{fill.hedging_order.exchange_order_id}] fill: unlocking "
                f"{locked_base if locked_base else locked_quote} {base if locked_base else quote} on [{self._trading_exchange_manager.exchange_name}]"
            )
            fill.is_locked = False
            summary = fill.get_summary(
                filled_hedging_order,
                self._hedging_exchange_manager,
                self._trading_exchange_manager,
            )
            self._logger.info(f"Completed hedging fill: {summary}")
            self._clear_completed_fills()
        else:
            self._logger.warning(
                f"No pending hedging fill found for order [{filled_hedging_order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]}]"
            )

    def _get_order_associated_hedging_fill(self, order: dict) -> typing.Optional[HedgingFill]:
        filled_order_exchange_id = order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
        for details in self._hedging_details_by_symbol.values():
            for fills in details.hedging_fills_by_order_id.values():
                for fill in fills:
                    if not fill.hedging_order:
                        continue
                    groupped_order_ids = [
                        order.exchange_order_id
                        for order in fill.hedging_order.order_group.get_group_open_orders()
                    ] if fill.hedging_order.order_group else []
                    if (
                        # this is the hedging order itself
                        fill.hedging_order.exchange_order_id == filled_order_exchange_id
                        # this is an order of the same group as the hedging order
                        or filled_order_exchange_id in groupped_order_ids
                    ):
                        return fill
        return None

    def _clear_completed_fills(self):
        trading_exchange_open_orders_exchange_ids = set[str](
            order.exchange_order_id
            for order in trading_api.get_open_orders(self._trading_exchange_manager)
        )
        for details in self._hedging_details_by_symbol.values():
            # remove elements from hedging_fills_by_order_id if all fills are completed
            # and the order is not open on the trading exchange anymore
            # to avoid letting the dict grow indefinitely
            for order_id in [
                order_id
                for order_id, fills in details.hedging_fills_by_order_id.items()
                if order_id not in trading_exchange_open_orders_exchange_ids
                if all(not fill.is_locked for fill in fills)
            ]:
                del details.hedging_fills_by_order_id[order_id]

    def _register_hedging_fill(self, order: dict) -> HedgingFill:
        details = self.get_symbol_details(order[trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value])
        hedging_price = details.last_hedging_price
        if hedging_price == trading_constants.ZERO:
            raise hedging_errors.HedgingPriceNotSetError(
                f"Hedging price is not set. This should not happen."
            )
        fill = HedgingFill(
            fill_trade=self.fill_trade_factory(
                self._trading_exchange_manager, order, self._get_newly_filled_amount(order), time.time()
            ),
            hedging_price=hedging_price,
        )
        details = self.get_symbol_details(fill.fill_trade.symbol)
        if fill.fill_trade.exchange_order_id not in details.hedging_fills_by_order_id:
            details.hedging_fills_by_order_id[fill.fill_trade.exchange_order_id] = []
        details.hedging_fills_by_order_id[fill.fill_trade.exchange_order_id].append(fill)
        self._logger.info(f"Registered hedging fill: {fill}")
        return fill

    @staticmethod
    def fill_trade_factory(
        trading_exchange_manager: trading_exchanges.ExchangeManager,
        order: dict,
        locally_filled_amount: decimal.Decimal,
        filled_time: float,
    ) -> personal_data.Trade:
        # 1. try to get a local copy of the real trade
        for trade in trading_exchange_manager.exchange_personal_data.trades_manager.get_trades(
            None, exchange_order_id=order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
        ):
            if trade.executed_quantity == locally_filled_amount and trade.executed_price == decimal.Decimal(str(order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])):
                # this is the locally filled trade: return a duplicate of it
                duplicate_trade = trade.duplicate()
                # force maker for the duplicate to use maker fees
                duplicate_trade.taker_or_maker = trading_enums.ExchangeConstantsOrderColumns.MAKER.value
                return duplicate_trade
        # 2. trade not found: create a local copy of the real trade
        logging.get_logger(HedgingEngine.__name__).info(
            f"Generating new trade from [{trading_exchange_manager.exchange_name}] order: {order}"
        )
        return personal_data.create_trade_from_dict(
            trading_exchange_manager.trader,
            {
                **order,
                trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value: locally_filled_amount,
                trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value: filled_time,
                trading_enums.ExchangeConstantsOrderColumns.TYPE.value: trading_enums.TradeOrderType.LIMIT.value,
                trading_enums.ExchangeConstantsOrderColumns.COST.value: locally_filled_amount * decimal.Decimal(str(order[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])),
                trading_enums.ExchangeConstantsOrderColumns.TAKER_OR_MAKER.value: trading_enums.ExchangeConstantsOrderColumns.MAKER.value,
            }
        )

    def _abort_hedging_fill(self, fill: HedgingFill):
        details = self.get_symbol_details(fill.fill_trade.symbol)
        details.hedging_fills_by_order_id[fill.fill_trade.exchange_order_id].remove(fill)
        if not details.hedging_fills_by_order_id[fill.fill_trade.exchange_order_id]:
            del details.hedging_fills_by_order_id[fill.fill_trade.exchange_order_id]
        if fill.fill_trade.exchange_order_id in details.aborted_hedging_fills_by_order_id:
            details.aborted_hedging_fills_by_order_id[fill.fill_trade.exchange_order_id].append(fill)
        else:
            details.aborted_hedging_fills_by_order_id[fill.fill_trade.exchange_order_id] = [fill]
        # todo later: handle aborted fills
        self._logger.warning(f"Aborted hedging fill: {fill}")
        self._logger.info(f"Updated aborted fills by order id: {details.aborted_hedging_fills_by_order_id}")

    def _get_newly_filled_amount(self, order: dict) -> decimal.Decimal:
        order_exchange_id = order[trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]
        already_counted_filled_amount = trading_constants.ZERO
        for details in self._hedging_details_by_symbol.values():
            if order_exchange_id in details.hedging_fills_by_order_id:
                for fill in details.hedging_fills_by_order_id[order_exchange_id]:
                    already_counted_filled_amount += fill.fill_trade.executed_quantity
            if order_exchange_id in details.aborted_hedging_fills_by_order_id:
                for aborted_fill in details.aborted_hedging_fills_by_order_id[order_exchange_id]:
                    already_counted_filled_amount += aborted_fill.fill_trade.executed_quantity
        newly_filled_amount = decimal.Decimal(str(order[trading_enums.ExchangeConstantsOrderColumns.FILLED.value])) - already_counted_filled_amount
        if newly_filled_amount <= trading_constants.ZERO:
            raise hedging_errors.HedgingAlreadyCountedFillAmountError(
                f"Newly filled amount is {newly_filled_amount}. This should not happen."
            )
        return newly_filled_amount

    def get_locked_base_and_quote(self, symbol: str) -> tuple[decimal.Decimal, decimal.Decimal]:
        # aggregate locked funds for all hedging symbols using this given symbol base or quote asset
        total_locked_base = total_locked_quote = trading_constants.ZERO
        base, quote = symbols_util.parse_symbol(symbol).base_and_quote()
        for details in self._hedging_details_by_symbol.values():
            if details.symbol.base == base or details.symbol.quote == quote:
                symbol_locked_base = symbol_locked_quote = trading_constants.ZERO
                for hedging_fills in details.hedging_fills_by_order_id.values():
                    for fill in hedging_fills:
                        fill_locked_base, fill_locked_quote = fill.get_locked_base_and_quote()
                        symbol_locked_base += fill_locked_base
                        symbol_locked_quote += fill_locked_quote
                for fills in details.aborted_hedging_fills_by_order_id.values():
                    for fill in fills:
                        fill_locked_base, fill_locked_quote = fill.get_locked_base_and_quote()
                        symbol_locked_base += fill_locked_base
                        symbol_locked_quote += fill_locked_quote
                if details.symbol.base == base:
                    total_locked_base += symbol_locked_base
                if details.symbol.quote == quote:
                    total_locked_quote += symbol_locked_quote
        return total_locked_base, total_locked_quote

    async def on_new_price(self, symbol: str, price: decimal.Decimal):
        details = self.get_symbol_details(symbol)
        details.last_hedging_price = price
        is_threshold_met, reason = details.volatility_threshold_checker.on_new_price(price)
        if is_threshold_met:
            await self._on_max_volatility_reached(symbol, reason)
        elif details.state is HedgingEngineState.MAX_VOLATILITY_REACHED:
            # resume hedging
            self._logger.info(
                f"Resuming hedging for [{symbol}] on [{self._hedging_exchange_manager.exchange_name}]: max volatility has passed."
            )
            details.state = HedgingEngineState.HEDGING

    def is_healthy(self, symbol: str) -> bool:
        return self.get_symbol_details(symbol).state is HedgingEngineState.HEDGING

    def reached_max_tolerated_volatility(self, symbol: str) -> bool:
        return self.get_symbol_details(symbol).state is HedgingEngineState.MAX_VOLATILITY_REACHED
    
    def get_critical_abnormal_state(self) -> typing.Optional[HedgingEngineState]:
        for details in self._hedging_details_by_symbol.values():
            if details.state in [
                HedgingEngineState.INITIALIZATION_FAILED,
                HedgingEngineState.MISSING_HEDGING_FUNDS,
                HedgingEngineState.STOPPED
            ]:
                return details.state
        return None

    def _get_base_and_quote_hedging_budget(self, details: SymbolHedgingDetails) -> tuple[decimal.Decimal, decimal.Decimal]:
        raise NotImplementedError("_get_base_and_quote_hedging_budget is not implemented")

    async def _on_max_volatility_reached(self, symbol: str, reason: str):
        explanation = (
            f"Max volatility reached for [{symbol}] on [{self._hedging_exchange_manager.exchange_name}]. "
            f"Reason: {reason}."
        )
        self._logger.info(
            f"{explanation} Switching to {HedgingEngineState.MAX_VOLATILITY_REACHED.value} state."
        )
        self._hedging_details_by_symbol[symbol].state = HedgingEngineState.MAX_VOLATILITY_REACHED
        raise hedging_errors.HedgingEngineReachedMaxToleratedVolatility(explanation)

    async def _wait_for_dependencies_if_required(self):
        await self._wait_for_hedging_exchange_manager()
        if not self._consumers:
            self._consumers = await self.create_consumers()
        await self._wait_for_hedging_funds()

    async def _async_start_for_hedging_details(self, details: SymbolHedgingDetails):
        await self._wait_for_dependencies_if_required()
        self._logger.info(
            f"Hedging engine starting for [{self._trading_exchange_manager.exchange_name}] using "
            f"[{self._hedging_exchange_manager.exchange_name}] as hedging exchange on "
            f"{details.symbol}"
        )
        try:
            self._ensure_hedging_funds(details)
            details.state = HedgingEngineState.HEDGING
        except hedging_errors.MissingHedgingFundsError as e:
            self._logger.error(
                f"Please add more funds on {self._hedging_exchange_manager.exchange_name} to use the hedging engine: {e}"
            )
            details.state = HedgingEngineState.MISSING_HEDGING_FUNDS
        except Exception as e:
            self._logger.exception(e, True, f"Error when starting hedging engine: {e}")
            details.state = HedgingEngineState.INITIALIZATION_FAILED
        finally:
            details.completed_initialization.set()

    def _ensure_hedging_funds(self, details: SymbolHedgingDetails):
        base_trading_budget, quote_trading_budget = self._get_base_and_quote_trading_budget(details)
        base_hedging_budget, quote_hedging_budget = self._get_base_and_quote_hedging_budget(details)
        # ensure hedging exchange has enough funds to hedge the trading exchange
        if base_hedging_budget < base_trading_budget or quote_hedging_budget < quote_trading_budget:
            base, quote = details.symbol.base_and_quote()
            raise hedging_errors.MissingHedgingFundsError(
                f"{details.symbol} [{self._hedging_exchange_manager.exchange_name}] hedging funds are not available. "
                f"{base} trading budget: {base_trading_budget} hedging budget: {base_hedging_budget}. "
                f"{quote} trading budget: {quote_trading_budget} hedging budget: {quote_hedging_budget}"
            )

    def _get_base_and_quote_trading_budget(
        self, details: SymbolHedgingDetails
    ) -> tuple[decimal.Decimal, decimal.Decimal]:
        base_available_holding = trading_api.get_portfolio_currency(
            self._trading_exchange_manager, details.symbol.base
        ).available
        quote_available_holding = trading_api.get_portfolio_currency(
            self._trading_exchange_manager, details.symbol.quote
        ).available
        return base_available_holding, quote_available_holding

    async def _wait_for_hedging_funds(self):
        # ensure both exchanges fetched their balances
        await trading_util.wait_for_topic_init(
            self._hedging_exchange_manager, BALANCE_INITIALIZATION_TIMEOUT,
            commons_enums.InitializationEventExchangeTopics.BALANCE.value
        )
        await trading_util.wait_for_topic_init(
            self._trading_exchange_manager, BALANCE_INITIALIZATION_TIMEOUT,
            commons_enums.InitializationEventExchangeTopics.BALANCE.value
        )
        self._logger.info(
            f"Hedging funds initialized for [{self._hedging_exchange_manager.exchange_name}] and [{self._trading_exchange_manager.exchange_name}]"
        )

    async def _wait_for_hedging_exchange_manager(self):
        t0 = time.time()
        while (hedging_exchange_manager := self._get_hedging_exchange_manager()) is None:
            await asyncio.sleep(0.5)
            self._logger.info(
                f"Waiting for [{self.hedging_exchange_name}] hedging exchange manager to be initialized. [{time.time() - t0:.2f}s]"
            )
        self._hedging_exchange_manager = hedging_exchange_manager

    def _get_hedging_exchange_manager(self) -> typing.Optional[trading_exchanges.ExchangeManager]:
        for exchange_id in trading_api.get_all_exchange_ids_with_same_matrix_id(
            self._trading_exchange_manager.exchange_name, self._trading_exchange_manager.id
        ):
            exchange_manager = trading_api.get_exchange_manager_from_exchange_id(exchange_id)
            if exchange_manager.exchange_name == self.hedging_exchange_name:
                return exchange_manager
        return None

    async def stop(self):
        for task in self._start_tasks:
            if not task.done():
                task.cancel()
        self._start_tasks.clear()
        to_remove_symbols = []
        for symbol in self._hedging_details_by_symbol:
            self._hedging_details_by_symbol[symbol].stop()
            to_remove_symbols.append(symbol)
        self._hedging_details_by_symbol = {
            symbol: details
            for symbol, details in self._hedging_details_by_symbol.items()
            if symbol not in to_remove_symbols
        }

        if not self._hedging_details_by_symbol:
            self._logger.info(
                f"Hedging engine stopped for [{self._trading_exchange_manager.exchange_name if self._trading_exchange_manager else 'unknown'} using "
                f"[{self._hedging_exchange_manager.exchange_name if self._hedging_exchange_manager else 'unknown'}] as hedging exchange: all hedging details have been stopped"
            )
            for consumer in self._consumers:
                await consumer.stop()
            self._consumers.clear()
            self._trading_exchange_manager = None # type: ignore
            self._hedging_exchange_manager = None # type: ignore

    def get_symbol_details(self, symbol: str) -> SymbolHedgingDetails:
        try:
            return self._hedging_details_by_symbol[symbol]
        except KeyError:
            raise hedging_errors.HedgingSymbolNotRegisteredError(f"Symbol [{symbol}] is not registered")

    async def create_consumers(self) -> list:
        # order consumer: triggered only on hedging exchange orders
        order_consumer = await exchanges_channel.get_chan(
            personal_data.OrdersChannel.get_name(), self._hedging_exchange_manager.id
        ).new_consumer(self._hedging_engine_order_notification_callback)
        return [order_consumer]
    
    async def _hedging_engine_order_notification_callback(
        self, exchange, exchange_id, cryptocurrency, symbol, order, update_type, is_from_bot
    ):
        if (
            order[trading_enums.ExchangeConstantsOrderColumns.STATUS.value] == trading_enums.OrderStatus.FILLED.value
        ):
            self._on_hedging_order_filled(order)
