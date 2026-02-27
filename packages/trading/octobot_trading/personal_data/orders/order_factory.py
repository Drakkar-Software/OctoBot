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
import dataclasses

import octobot_commons.logging as logging
import octobot_commons.signals as commons_signals

import octobot_trading.personal_data as personal_data
import octobot_trading.enums as enums
import octobot_trading.constants as constants
import octobot_trading.errors as trading_errors
import octobot_trading.modes.script_keywords as script_keywords

if typing.TYPE_CHECKING:
    import octobot_trading.exchanges
    import octobot_trading.modes


def create_order_from_raw(
    trader: "octobot_trading.exchanges.Trader",
    raw_order: dict,
) -> "personal_data.Order":
    _, order_type = personal_data.parse_order_type(raw_order)
    if not order_type:
        logging.get_logger(__name__).error(
            f"Unhandled order type: {raw_order.get(enums.ExchangeConstantsOrderColumns.TYPE.value)} ({raw_order=})"
        )
    return create_order_from_type(trader, order_type)


def create_order_instance_from_raw(
    trader: "octobot_trading.exchanges.Trader",
    raw_order: dict,
    force_open_or_pending_creation: bool = False,
    has_just_been_created: bool = False,
) -> "personal_data.Order":
    try:
        order = create_order_from_raw(trader, raw_order)
        order.update_from_raw(raw_order)
        if has_just_been_created:
            order.register_broker_applied_if_enabled()
        if force_open_or_pending_creation \
                and order.status not in (enums.OrderStatus.OPEN, enums.OrderStatus.PENDING_CREATION):
            order.status = enums.OrderStatus.OPEN
        return order
    except Exception as err:
        # log unparsable order to fix it
        logging.get_logger(__name__).exception(
            err, True, f"Unexpected {err} ({err.__class__.__name__}) error when parsing row order {raw_order}"
        )
        raise


def create_order_from_type(
    trader: "octobot_trading.exchanges.Trader",
    order_type: enums.TraderOrderType,
    side: typing.Optional[enums.TradeOrderSide] = None,
) -> "personal_data.Order":
    if side is None:
        return personal_data.TraderOrderTypeClasses[order_type](trader)
    return personal_data.TraderOrderTypeClasses[order_type](trader, side=side)


def create_order_instance(
    trader: "octobot_trading.exchanges.Trader",
    order_type: enums.TraderOrderType,
    symbol: str,
    current_price: decimal.Decimal,
    quantity: decimal.Decimal,
    price: decimal.Decimal = constants.ZERO,
    stop_price: decimal.Decimal = constants.ZERO,
    status: enums.OrderStatus = enums.OrderStatus.OPEN,
    order_id: typing.Optional[str] = None,
    exchange_order_id: typing.Optional[str] = None,
    filled_price: decimal.Decimal = constants.ZERO,
    average_price: decimal.Decimal = constants.ZERO,
    quantity_filled: decimal.Decimal = constants.ZERO,
    total_cost: decimal.Decimal = constants.ZERO,
    timestamp: int = 0,
    side: typing.Optional[enums.TradeOrderSide] = None,
    trigger_above: typing.Optional[bool] = None,
    fees_currency_side: typing.Optional[str] = None,
    group: typing.Optional[str] = None,
    tag: typing.Optional[str] = None,
    reduce_only: typing.Optional[bool] = None,
    quantity_currency: typing.Optional[str] = None,
    close_position: bool = False,
    exchange_creation_params: typing.Optional[dict] = None,
    associated_entry_id: typing.Optional[str] = None,
    trailing_profile: typing.Optional["personal_data.TrailingProfile"] = None,
    is_active: typing.Optional[bool] = None,
    active_trigger_price: typing.Optional[decimal.Decimal] = None,
    active_trigger_above: typing.Optional[bool] = None,
    cancel_policy: typing.Optional["personal_data.OrderCancelPolicy"] = None,
) -> "personal_data.Order":
    order = create_order_from_type(trader, order_type, side=side)
    order.update(
        order_type=order_type,
        symbol=symbol,
        current_price=current_price,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        order_id=trader.parse_order_id(order_id),
        exchange_order_id=exchange_order_id,
        timestamp=timestamp,
        status=status,
        filled_price=filled_price,
        average_price=average_price,
        quantity_filled=quantity_filled,
        fee=None,
        total_cost=total_cost,
        fees_currency_side=fees_currency_side,
        group=group,
        tag=tag,
        reduce_only=reduce_only,
        quantity_currency=quantity_currency,
        close_position=close_position,
        exchange_creation_params=exchange_creation_params,
        associated_entry_id=associated_entry_id,
        trigger_above=trigger_above,
        trailing_profile=trailing_profile,
        is_active=is_active,
        active_trigger=personal_data.create_order_price_trigger(order, active_trigger_price, active_trigger_above)
            if active_trigger_price else None,
        cancel_policy=cancel_policy,
    )
    return order


def create_order_from_dict(
    trader: "octobot_trading.exchanges.Trader",
    order_dict: dict,
) -> "personal_data.Order":
    """
    :param trader: the trader to associate the order to
    :param order_dict: a dict formatted as from order.to_dict()
    :return: the created order instance
    """
    _, order_type = personal_data.parse_order_type(order_dict)
    return create_order_instance(
        trader,
        order_type,
        order_dict[enums.ExchangeConstantsOrderColumns.SYMBOL.value],
        constants.ZERO,
        order_dict[enums.ExchangeConstantsOrderColumns.AMOUNT.value],
        price=order_dict[enums.ExchangeConstantsOrderColumns.PRICE.value],
        status=enums.OrderStatus(order_dict[enums.ExchangeConstantsOrderColumns.STATUS.value]),
        order_id=order_dict[enums.ExchangeConstantsOrderColumns.ID.value],
        exchange_order_id=order_dict.get(enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value),
        quantity_filled=order_dict[enums.ExchangeConstantsOrderColumns.FILLED.value],
        timestamp=order_dict[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value],
        side=enums.TradeOrderSide(order_dict[enums.ExchangeConstantsOrderColumns.SIDE.value]),
        trigger_above=order_dict.get(enums.ExchangeConstantsOrderColumns.TRIGGER_ABOVE.value),
        tag=order_dict[enums.ExchangeConstantsOrderColumns.TAG.value],
        reduce_only=order_dict[enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value],
    )


async def create_order_from_order_storage_details(
    order_storage_details: dict,
    exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    pending_groups: dict,
) -> "personal_data.Order":
    order = create_order_from_dict(
        exchange_manager.trader,
        order_storage_details[constants.STORAGE_ORIGIN_VALUE]
    )
    order.update_from_storage_order_details(order_storage_details)
    await personal_data.create_orders_storage_related_elements(
        order, order_storage_details, exchange_manager, pending_groups
    )
    return order


async def restore_chained_orders_from_storage_order_details(
    order: "personal_data.Order",
    order_details: dict,
    exchange_manager: "octobot_trading.exchanges.ExchangeManager",
    pending_groups: dict,
) -> None:
    chained_orders = order_details.get(enums.StoredOrdersAttr.CHAINED_ORDERS.value, None)
    if chained_orders:
        for chained_order in chained_orders:
            chained_order_inst = await create_order_from_order_storage_details(
                chained_order, exchange_manager, pending_groups
            )
            await chained_order_inst.set_as_chained_order(
                order,
                chained_order.get(enums.StoredOrdersAttr.HAS_BEEN_BUNDLED.value, False),
                chained_order.get(enums.StoredOrdersAttr.EXCHANGE_CREATION_PARAMS.value, {}),
                chained_order.get(enums.StoredOrdersAttr.UPDATE_WITH_TRIGGERING_ORDER_FEES.value, False),
                **chained_order.get(enums.StoredOrdersAttr.TRADER_CREATION_KWARGS.value, {}),
            )
            order.add_chained_order(chained_order_inst)
            logging.get_logger(order.get_logger_name()).debug(f"Restored chained order: {chained_order_inst}")


@dataclasses.dataclass
class _OrderDetails:
    def __init__(self, input_price: decimal.Decimal, input_quantity_ratio: decimal.Decimal):
        self.input_price = input_price
        self.input_quantity_ratio = input_quantity_ratio


class OrderFactory:
    def __init__(
        self,
        exchange_manager: typing.Optional["octobot_trading.exchanges.ExchangeManager"],
        trading_mode: typing.Optional["octobot_trading.modes.AbstractTradingMode"],
        dependencies: typing.Optional[commons_signals.SignalDependencies],
        wait_for_creation: bool,
        try_to_handle_unconfigured_symbol: bool,
    ):
        self.exchange_manager: "octobot_trading.exchanges.ExchangeManager" = exchange_manager # type: ignore
        self.trading_mode: typing.Optional["octobot_trading.modes.AbstractTradingMode"] = trading_mode
        self.dependencies: typing.Optional[commons_signals.SignalDependencies] = dependencies
        self.wait_for_creation: bool = wait_for_creation
        self.try_to_handle_unconfigured_symbol: bool = try_to_handle_unconfigured_symbol

    def validate(self) -> None:
        if self.exchange_manager is None:
            raise ValueError(
                f"exchange_manager is required to use {self.__class__.__name__}"
            )

    def _get_validated_amounts_and_prices(
        self, symbol: str, amount: decimal.Decimal, price: decimal.Decimal, symbol_market
    ) -> list[tuple[decimal.Decimal, decimal.Decimal]]:
        quantities_and_prices = personal_data.decimal_check_and_adapt_order_details_if_necessary(
            amount, price, symbol_market
        )
        if len(quantities_and_prices) == 0:
            min_amount = personal_data.get_minimal_order_amount(symbol_market)
            if amount < min_amount:
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"An order amount of {amount} is too small to trade {symbol} on {self.exchange_manager.exchange_name}. Minimum amount is {min_amount}."
                )
            cost = price * amount
            min_cost = personal_data.get_minimal_order_cost(symbol_market)
            if cost < min_cost:
                raise trading_errors.MissingMinimalExchangeTradeVolume(
                    f"An order cost of {cost} is too small to trade {symbol} on {self.exchange_manager.exchange_name}. Minimum cost is {min_cost}."
                )
        return quantities_and_prices

    async def _get_computed_price(self, ctx: script_keywords.Context, order_price: str) -> decimal.Decimal:
        return await script_keywords.get_price_with_offset(ctx, order_price, use_delta_type_as_flat_value=True)

    async def _get_computed_quantity(
        self, ctx: script_keywords.Context, input_amount: str, 
        side: enums.TradeOrderSide, target_price: decimal.Decimal, 
        reduce_only: bool, allow_holdings_adaptation: bool
    ):
        if not input_amount or input_amount == "0":
            return constants.ZERO
        return await script_keywords.get_amount_from_input_amount(
            context=ctx,
            input_amount=input_amount,
            side=side.value,
            reduce_only=reduce_only,
            is_stop_order=False,
            use_total_holding=False,
            target_price=target_price,
            # raise when not enough funds to create an order according to user input
            allow_holdings_adaptation=allow_holdings_adaptation,
        )

    def _ensure_supported_order_type(self, order_type: enums.TraderOrderType):
        if not self.exchange_manager.exchange.is_supported_order_type(order_type):
            raise trading_errors.NotSupportedOrderTypeError(
                f"{order_type.name} orders are not supported on {self.exchange_manager.exchange_name}", 
                order_type
            )

    async def _create_stop_orders(
        self, ctx: script_keywords.Context,
        base_order: "personal_data.Order",
        symbol_market: dict,
        params: dict, chained_orders: list["personal_data.Order"],
        stop_loss_price: typing.Optional[decimal.Decimal] = None,
    ):
        if not stop_loss_price:
            return
        self._ensure_supported_order_type(enums.TraderOrderType.STOP_LOSS)
        computed_stop_price = await self._get_computed_price(ctx, stop_loss_price)
        adapted_stop_price = personal_data.decimal_adapt_price(
            symbol_market, computed_stop_price
        )
        exit_side = (
            enums.TradeOrderSide.SELL 
            if base_order.side == enums.TradeOrderSide.BUY else enums.TradeOrderSide.BUY
        )
        param_update, chained_order = await personal_data.create_and_register_chained_order_on_base_order(
            base_order, adapted_stop_price, enums.TraderOrderType.STOP_LOSS, exit_side,
            quantity=base_order.origin_quantity, tag=base_order.tag,
            reduce_only=self.exchange_manager.is_future,
        )
        params.update(param_update)
        chained_orders.append(chained_order)

    async def _create_take_profit_orders(
        self,
        ctx: script_keywords.Context,
        base_order: "personal_data.Order",
        symbol_market: dict,
        params: dict,
        chained_orders: list["personal_data.Order"],
        take_profit_prices: typing.Optional[list[decimal.Decimal]] = None,
        take_profit_volume_percents: typing.Optional[list[decimal.Decimal]] = None,
    ):
        if not take_profit_prices:
            return
        take_profit_volume_percents = take_profit_volume_percents or []
        if len(take_profit_volume_percents) not in (0, len(take_profit_prices)):
            raise trading_errors.InvalidArgumentError(
                f"There must be either 0 or as many take profit volume percents as take profit prices"
            )
        exit_side = (
            enums.TradeOrderSide.SELL 
            if base_order.side == enums.TradeOrderSide.BUY else enums.TradeOrderSide.BUY
        )
        total_take_profit_volume_percent = decimal.Decimal(str(sum(
            float(v) for v in take_profit_volume_percents)
        ))
        take_profit_order_details = [
            _OrderDetails(
                take_profit_price,
                (decimal.Decimal(str(take_profit_volume_percents[i])) / total_take_profit_volume_percent) if total_take_profit_volume_percent else (
                    constants.ONE / len(take_profit_prices)
                )
            )
            for i, take_profit_price in enumerate(take_profit_prices)
        ]
        for index, take_profits_detail in enumerate(take_profit_order_details):
            is_last = index == len(take_profit_order_details) - 1
            price = await self._get_computed_price(ctx, take_profits_detail.input_price)
            quantity = personal_data.decimal_adapt_quantity(
                symbol_market, base_order.origin_quantity * take_profits_detail.input_quantity_ratio
            )
            order_type = self.exchange_manager.trader.get_take_profit_order_type(
                base_order,
                enums.TraderOrderType.SELL_LIMIT if exit_side is enums.TradeOrderSide.SELL
                else enums.TraderOrderType.BUY_LIMIT
            )
            param_update, chained_order = await personal_data.create_and_register_chained_order_on_base_order(
                base_order, price, order_type, exit_side,
                quantity=quantity, tag=base_order.tag, reduce_only=self.exchange_manager.is_future,
                # only the last order is to take trigger fees into account
                update_with_triggering_order_fees=is_last and not self.exchange_manager.is_future
            )
            params.update(param_update)
            chained_orders.append(chained_order)

    def _create_active_order_swap_strategy(
        self,
        active_order_swap_strategy_type: typing.Optional[str] = None,
        active_order_swap_strategy_params: typing.Optional[dict] = None
    ) -> "personal_data.ActiveOrderSwapStrategy":
        return personal_data.create_active_order_swap_strategy(
            active_order_swap_strategy_type, **(active_order_swap_strategy_params or {})
        )

    async def _create_base_order_associated_elements(
        self,
        base_order: "personal_data.Order",
        ctx: script_keywords.Context,
        symbol_market: dict,
        stop_loss_price: typing.Optional[decimal.Decimal] = None,
        take_profit_prices: typing.Optional[list[decimal.Decimal]] = None,
        take_profit_volume_percents: typing.Optional[list[decimal.Decimal]] = None,
        trailing_profile_type: typing.Optional[str] = None,
        active_order_swap_strategy_type: typing.Optional[str] = None,
        active_order_swap_strategy_params: typing.Optional[dict] = None,
    ) -> None:
        # create chained orders
        params = {}
        chained_orders = []
        await self._create_stop_orders(
            ctx, base_order, symbol_market, params, chained_orders, stop_loss_price
        )
        await self._create_take_profit_orders(
            ctx, base_order, symbol_market, params, chained_orders, take_profit_prices, take_profit_volume_percents
        )
        stop_orders = [o for o in chained_orders if personal_data.is_stop_order(o.order_type)]
        tp_orders = [o for o in chained_orders if not personal_data.is_stop_order(o.order_type)]
        if stop_orders and tp_orders:

            active_order_swap_strategy = self._create_active_order_swap_strategy(
                active_order_swap_strategy_type, active_order_swap_strategy_params
            )
            if len(stop_orders) == len(tp_orders):
                group_type = personal_data.OneCancelsTheOtherOrderGroup
            elif trailing_profile_type == personal_data.TrailingProfileTypes.FILLED_TAKE_PROFIT.value:
                group_type = personal_data.TrailingOnFilledTPBalancedOrderGroup
                entry_price = base_order.origin_price
                for stop_order in stop_orders:
                    # register trailing profile in stop orders
                    stop_order.trailing_profile = personal_data.create_filled_take_profit_trailing_profile(
                        entry_price, tp_orders
                    )
            else:
                group_type = personal_data.BalancedTakeProfitAndStopOrderGroup
            oco_group = self.exchange_manager.exchange_personal_data.orders_manager.create_group(
                group_type, active_order_swap_strategy=active_order_swap_strategy
            )
            for order in chained_orders:
                order.add_to_order_group(oco_group)
            # in futures, inactive orders are not necessary
            if self.exchange_manager.trader.enable_inactive_orders and not self.exchange_manager.is_future:
                await oco_group.active_order_swap_strategy.apply_inactive_orders(chained_orders)


    async def create_base_orders_and_associated_elements(
        self,
        order_type: enums.TraderOrderType,
        symbol: str,
        side: enums.TradeOrderSide,
        amount: str,
        price: typing.Optional[decimal.Decimal] = None,
        reduce_only: bool = False,
        allow_holdings_adaptation: bool = False,
        tag: typing.Optional[str] = None,
        exchange_creation_params: typing.Optional[dict] = None,
        cancel_policy: typing.Optional["personal_data.OrderCancelPolicy"] = None,
        stop_loss_price: typing.Optional[decimal.Decimal] = None,
        take_profit_prices: typing.Optional[list[decimal.Decimal]] = None,
        take_profit_volume_percents: typing.Optional[list[decimal.Decimal]] = None,
        trailing_profile_type: typing.Optional[str] = None,
        active_order_swap_strategy_type: typing.Optional[str] = None,
        active_order_swap_strategy_params: typing.Optional[dict] = None,
    ) -> list["personal_data.Order"]:
        if symbol not in self.exchange_manager.exchange_symbols_data.exchange_symbol_data:
            if self.try_to_handle_unconfigured_symbol:
                raise NotImplementedError("try_to_handle_unconfigured_symbol is not yet implemented")
            else:
                raise trading_errors.UnSupportedSymbolError(
                    f"Symbol {symbol} not found in exchange traded symbols. Available symbols: "
                    f"{', '.join(self.exchange_manager.exchange_symbols_data.exchange_symbol_data)}"
                )
        current_price = await personal_data.get_up_to_date_price(
            self.exchange_manager, symbol=symbol, timeout=constants.ORDER_DATA_FETCHING_TIMEOUT
        )
        symbol_market = self.exchange_manager.exchange.get_market_status(symbol, with_fixer=False)
        ctx = script_keywords.get_base_context_from_exchange_manager(self.exchange_manager, symbol)
            # market orders have no price
        computed_price = current_price if price is None else await self._get_computed_price(ctx, price)
        computed_amount = await self._get_computed_quantity(
            ctx, amount, side, computed_price, reduce_only, allow_holdings_adaptation=allow_holdings_adaptation
        )
        valid_amount_and_prices = self._get_validated_amounts_and_prices(
            symbol, computed_amount, computed_price, symbol_market
        )
        base_orders = []
        for valid_amount, valid_price in valid_amount_and_prices:
            base_order = personal_data.create_order_instance(
                trader=self.exchange_manager.trader,
                order_type=order_type,
                symbol=symbol,
                current_price=current_price,
                quantity=valid_amount,
                price=valid_price,
                side=side,
                tag=tag,
                reduce_only=reduce_only,
                exchange_creation_params=exchange_creation_params,
                cancel_policy=cancel_policy,
            )
            await self._create_base_order_associated_elements(
                base_order,
                ctx,
                symbol_market,
                stop_loss_price,
                take_profit_prices,
                take_profit_volume_percents,
                trailing_profile_type,
                active_order_swap_strategy_type,
                active_order_swap_strategy_params,
            )
            base_orders.append(base_order)
        return base_orders

    async def create_order_on_exchange(
        self, order: "personal_data.Order",
    ) -> typing.Optional["personal_data.Order"]:
        return (
            await self.trading_mode.create_order(
                order, dependencies=self.dependencies, wait_for_creation=self.wait_for_creation
            ) if self.trading_mode else (
                await self.exchange_manager.trader.create_order(order, wait_for_creation=self.wait_for_creation)
            )
        )
    
    def _logger(self) -> logging.BotLogger:
        return logging.get_logger(f"{self.__class__.__name__} | {self.exchange_manager.exchange_name}")
