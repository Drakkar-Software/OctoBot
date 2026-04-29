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
from ccxt.base.types import (
    # usual "import ccxt.base.types" is not working here from ... import ... is required
    Order as CCXTOrder,
    Ticker as CCXTTicker,
    Balances as CCXTBalances,
    OrderBook as CCXTOrderBook,
    Trade as CCXTTrade,
    Position as CCXTPosition,
    FundingRate as CCXTFundingRate,
    Leverage as CCXTLeverage,
    LeverageTiers as CCXTLeverageTiers,
    Market as CCXTMarket,
    Transaction as CCXTTransaction,
    DepositAddress as CCXTDepositAddress,
    FundingRates as CCXTFundingRates,
)

import octobot_trading.exchanges.adapters as adapters
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.personal_data as personal_data
import octobot_trading.constants as constants
import octobot_trading.enums as enums
from octobot_trading.enums import ExchangeConstantsOrderColumns as ecoc
import octobot_commons.enums as common_enums
import octobot_commons.constants as common_constants
import octobot_commons.number_util as number_util


class CCXTAdapter(adapters.AbstractAdapter):
    def fix_order(self, raw: CCXTOrder, symbol=None, **kwargs) -> dict:
        fixed = super().fix_order(raw, **kwargs)
        try:
            exchange_timestamp = fixed[ecoc.TIMESTAMP.value]
            fixed[ecoc.TIMESTAMP.value] = self.get_uniformized_timestamp(exchange_timestamp)
            self.adapt_quantities_with_contract_size(fixed, symbol)
        except KeyError as e:
            self.logger.error(f"Fail to cleanup order dict ({e})")
        self._register_exchange_fees(fixed)
        return fixed

    def parse_order(self, fixed: CCXTOrder, **kwargs) -> dict:
        # CCXT standard order parsing logic
        return fixed # type: ignore

    def adapt_amount_from_filled_or_cost(self, fixed: dict) -> None:
        try:
            if (
                fixed[enums.ExchangeConstantsOrderColumns.TYPE.value] == enums.TradeOrderType.MARKET.value and
                fixed[enums.ExchangeConstantsOrderColumns.SIDE.value] == enums.TradeOrderSide.BUY.value and
                fixed[enums.ExchangeConstantsOrderColumns.FILLED.value]
            ):
                # convert amount to use the base unit: use FILLED for accuracy (when not None/0)
                fixed[enums.ExchangeConstantsOrderColumns.AMOUNT.value] = (
                    fixed[enums.ExchangeConstantsOrderColumns.FILLED.value]
                )
            if (
                (not fixed[enums.ExchangeConstantsOrderColumns.AMOUNT.value]) and
                fixed[enums.ExchangeConstantsOrderColumns.COST.value] and
                fixed[enums.ExchangeConstantsOrderColumns.PRICE.value]
            ):
                # convert amount to use the base unit
                fixed[enums.ExchangeConstantsOrderColumns.AMOUNT.value] = (
                    fixed[enums.ExchangeConstantsOrderColumns.COST.value] /
                    fixed[enums.ExchangeConstantsOrderColumns.PRICE.value]
                )
        except KeyError:
            pass

    def adapt_quantities_with_contract_size(self, order_or_trade: dict, symbol: str) -> None:
        if self.connector.exchange_manager.is_future:
            used_symbol = symbol or order_or_trade.get(ecoc.SYMBOL.value)
            if used_symbol is None:
                # can't get contract size
                return
            # amount is in contacts, multiply by contract value to get the currency amount (displayed to the user)
            contract_size = self.connector.get_contract_size(used_symbol)
            if contract_size == constants.ONE:
                # nothing to do
                return
            if amount := order_or_trade.get(enums.ExchangeConstantsOrderColumns.AMOUNT.value):
                order_or_trade[enums.ExchangeConstantsOrderColumns.AMOUNT.value] = amount * float(contract_size)
            if filled := order_or_trade.get(enums.ExchangeConstantsOrderColumns.FILLED.value):
                order_or_trade[enums.ExchangeConstantsOrderColumns.FILLED.value] = filled * float(contract_size)

    def _register_exchange_fees(self, order_or_trade: dict) -> None:
        try:
            fees = order_or_trade[enums.ExchangeConstantsOrderColumns.FEE.value]
            fees[enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value] = fees[enums.FeePropertyColumns.COST.value]
            fees[enums.FeePropertyColumns.IS_FROM_EXCHANGE.value] = True
        except (KeyError, TypeError):
            pass

    def _ensure_fees(self, order_or_trade: dict) -> None:
        # call if necessary
        if order_or_trade.get(enums.ExchangeConstantsOrderColumns.FEE.value) is None:
            order_or_trade[enums.ExchangeConstantsOrderColumns.FEE.value] = {
                enums.FeePropertyColumns.COST.value: constants.ZERO,
                enums.FeePropertyColumns.EXCHANGE_ORIGINAL_COST.value: constants.ZERO,
                enums.FeePropertyColumns.CURRENCY.value: None,
                enums.FeePropertyColumns.RATE.value: None,
                enums.FeePropertyColumns.TYPE.value: ccxt_enums.ExchangeOrderCCXTColumns.TAKER_OR_MAKER.value,
                enums.FeePropertyColumns.IS_FROM_EXCHANGE.value: True,
            }

    def _fix_ohlcv_prices(self, ohlcv: list[float]) -> None:
        for index, value in enumerate(ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value + 1:]):
            ohlcv[index + 1] = float(value)

    def fix_ohlcv(self, raw: list[dict], **kwargs) -> list[dict]:
        fixed = super().fix_ohlcv(raw, **kwargs)
        # ensure open time is not the current time but the actual candle open time
        # time_frame kwarg has to be passed to parse candle time
        candles_s = 1
        if "time_frame" in kwargs:
            candles_s = common_enums.TimeFramesMinutes[common_enums.TimeFrames(kwargs["time_frame"])] * \
                        common_constants.MINUTE_TO_SECONDS
        for index, ohlcv in enumerate(fixed):
            try:
                int_val = int(self.get_uniformized_timestamp(ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value]))
                ohlcv[common_enums.PriceIndexes.IND_PRICE_TIME.value] = int_val - (int_val % candles_s)
                self._fix_ohlcv_prices(ohlcv)
            except TypeError:
                # the last candle might not be properly set
                if self.connector.exchange_manager.exchange.DUMP_INCOMPLETE_LAST_CANDLE and index == len(fixed) - 1:
                    return fixed[:-1]
                raise
            except KeyError as e:
                self.logger.error(f"Fail to fix ohlcv ({e})")
        return fixed

    def parse_ohlcv(self, fixed: list[dict], **kwargs) -> list[dict]:
        # CCXT standard ohlcv parsing logic
        return fixed

    def fix_kline(self, raw: dict, **kwargs) -> dict:
        fixed = super().fix_kline(raw, **kwargs)
        for index, kline in enumerate(fixed):
            try:
                kline[common_enums.PriceIndexes.IND_PRICE_TIME.value] = \
                    int(self.get_uniformized_timestamp(kline[common_enums.PriceIndexes.IND_PRICE_TIME.value]))
                self._fix_ohlcv_prices(kline)
            except TypeError:
                # the last candle might not be properly set
                if self.connector.exchange_manager.exchange.DUMP_INCOMPLETE_LAST_CANDLE and index == len(fixed) - 1:
                    return fixed[:-1]
                raise
            except KeyError as e:
                self.logger.error(f"Fail to fix kline ({e})")
        return fixed

    def parse_kline(self, fixed: dict, **kwargs) -> dict:
        # CCXT standard kline parsing logic
        return fixed

    def fix_ticker(self, raw: CCXTTicker, **kwargs) -> dict:
        fixed = super().fix_ticker(raw, **kwargs)
        # CCXT standard ticker fixing logic
        if timestamp := fixed.get(enums.ExchangeConstantsTickersColumns.TIMESTAMP.value):
            fixed[enums.ExchangeConstantsTickersColumns.TIMESTAMP.value] = \
                int(self.get_uniformized_timestamp(timestamp))
        return fixed

    def parse_ticker(self, fixed: CCXTTicker, **kwargs) -> dict:
        # CCXT standard ticker parsing logic
        return fixed # type: ignore

    def create_ticker_from_kline(self, kline: list[float], symbol: str, **kwargs) -> dict:
        return {
            enums.ExchangeConstantsTickersColumns.SYMBOL.value: symbol,
            enums.ExchangeConstantsTickersColumns.TIMESTAMP.value: kline[common_enums.PriceIndexes.IND_PRICE_TIME.value],
            enums.ExchangeConstantsTickersColumns.OPEN.value: kline[common_enums.PriceIndexes.IND_PRICE_OPEN.value],
            enums.ExchangeConstantsTickersColumns.HIGH.value: kline[common_enums.PriceIndexes.IND_PRICE_HIGH.value],
            enums.ExchangeConstantsTickersColumns.LOW.value: kline[common_enums.PriceIndexes.IND_PRICE_LOW.value],
            enums.ExchangeConstantsTickersColumns.CLOSE.value: kline[common_enums.PriceIndexes.IND_PRICE_CLOSE.value],
            enums.ExchangeConstantsTickersColumns.BASE_VOLUME.value: kline[common_enums.PriceIndexes.IND_PRICE_VOL.value],
            enums.ExchangeConstantsTickersColumns.LAST.value: kline[common_enums.PriceIndexes.IND_PRICE_CLOSE.value],
            enums.ExchangeConstantsTickersColumns.BID.value: None,
            enums.ExchangeConstantsTickersColumns.BID_VOLUME.value: None,
            enums.ExchangeConstantsTickersColumns.ASK.value: None,
            enums.ExchangeConstantsTickersColumns.ASK_VOLUME.value: None,
            enums.ExchangeConstantsTickersColumns.PREVIOUS_CLOSE.value: None,
        }

    def fix_balance(self, raw: CCXTBalances, **kwargs) -> dict:
        fixed = super().fix_balance(raw, **kwargs)
        # remove not currency specific keys
        return fixed

    def parse_balance(self, fixed: CCXTBalances, **kwargs) -> dict:
        fixed.pop(constants.CONFIG_PORTFOLIO_FREE, None)
        fixed.pop(constants.CONFIG_PORTFOLIO_USED, None)
        fixed.pop(constants.CONFIG_PORTFOLIO_TOTAL, None)
        fixed.pop(ccxt_constants.CCXT_INFO, None)
        fixed.pop(ccxt_enums.ExchangeConstantsCCXTColumns.DATETIME.value, None)
        fixed.pop(ccxt_enums.ExchangeConstantsCCXTColumns.TIMESTAMP.value, None)
        return personal_data.parse_decimal_portfolio(fixed)

    def fix_order_book(self, raw: CCXTOrderBook, **kwargs) -> dict:
        fixed = super().fix_order_book(raw, **kwargs)
        # CCXT standard order_book fixing logic
        try:
            exchange_timestamp = fixed[enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value]
            if exchange_timestamp is None:
                # force current time
                fixed[enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value] =  self.connector.get_exchange_current_time()
            else:
                fixed[enums.ExchangeConstantsOrderBookInfoColumns.TIMESTAMP.value] = self.get_uniformized_timestamp(
                    exchange_timestamp
                )
        except KeyError as e:
            self.logger.error(f"Fail to convert order book timestamp ({e})")
        return fixed

    def parse_order_book(self, fixed: CCXTOrderBook, **kwargs) -> dict:
        # CCXT standard order_book parsing logic
        return fixed # type: ignore

    def fix_public_recent_trades(self, raw: list[CCXTTrade], **kwargs) -> list[dict]:
        fixed = super().fix_public_recent_trades(raw, **kwargs)
        # CCXT standard public_recent_trades fixing logic
        for recent_trade in fixed:
            try:
                recent_trade[ecoc.TIMESTAMP.value] = \
                    self.get_uniformized_timestamp(recent_trade[ecoc.TIMESTAMP.value])
            except KeyError as e:
                self.logger.error(f"Fail to clean recent_trade dict ({e})")
        return fixed

    def parse_public_recent_trades(self, fixed: list[CCXTTrade], **kwargs) -> list[dict]:
        # CCXT standard public_recent_trades parsing logic
        for recent_trade in fixed:
            recent_trade.pop(ecoc.INFO.value, None)
            recent_trade.pop(ecoc.DATETIME.value, None)
            recent_trade.pop(ecoc.EXCHANGE_ID.value, None)
            recent_trade.pop(ecoc.ID.value, None)
            recent_trade.pop(ecoc.ORDER.value, None)
            recent_trade.pop(ecoc.FEE.value, None)
            recent_trade.pop(ecoc.TYPE.value, None)
            recent_trade.pop(ecoc.TAKER_OR_MAKER.value, None)
        return fixed # type: ignore

    def fix_trades(self, raw: list[dict], **kwargs) -> list[dict]:
        fixed = super().fix_trades(raw, **kwargs)
        # CCXT standard trades fixing logic
        for trade in fixed:
            try:
                trade[ecoc.TIMESTAMP.value] = \
                    self.get_uniformized_timestamp(trade[ecoc.TIMESTAMP.value])
                trade[ecoc.EXCHANGE_ID.value] = trade.get(ecoc.ORDER.value)
                if trade[enums.ExchangeConstantsOrderColumns.TYPE.value] is None:
                    trade[enums.ExchangeConstantsOrderColumns.TYPE.value] = enums.TradeOrderType.MARKET.value \
                        if trade[ccxt_enums.ExchangeOrderCCXTColumns.TAKER_OR_MAKER.value] \
                        == enums.ExchangeConstantsMarketPropertyColumns.TAKER.value \
                        else enums.TradeOrderType.LIMIT.value
                self.adapt_quantities_with_contract_size(trade, None)
            except KeyError as e:
                self.logger.error(f"Fail to clean trade dict ({e})")
            self._register_exchange_fees(trade)
        return fixed

    def parse_trades(self, fixed: list[dict], **kwargs) -> list[dict]:
        # CCXT standard trades parsing logic
        return fixed

    def fix_position(self, raw: CCXTPosition, **kwargs) -> dict:
        fixed = super().fix_position(raw, **kwargs)
        # CCXT standard position fixing logic
        return fixed

    def parse_position(self, fixed: CCXTPosition, force_empty: bool = False, **kwargs) -> dict:
        # CCXT standard position parsing logic
        # if mode is enums.PositionMode.ONE_WAY:
        original_side = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.SIDE.value)
        symbol = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.SYMBOL.value)
        contract_size = decimal.Decimal(str(fixed.get(ccxt_enums.ExchangePositionCCXTColumns.CONTRACT_SIZE.value, 0) or 0))
        contracts = constants.ZERO if force_empty \
            else decimal.Decimal(str(fixed.get(ccxt_enums.ExchangePositionCCXTColumns.CONTRACTS.value, 0) or 0))
        is_empty = contracts == constants.ZERO
        position_mode = (
            enums.PositionMode.HEDGE if fixed.get(ccxt_enums.ExchangePositionCCXTColumns.HEDGED.value, False)
            else enums.PositionMode.ONE_WAY
        )
        if position_mode is enums.PositionMode.HEDGE:
            # todo when handling hedge positions
            side = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.SIDE.value, enums.PositionSide.UNKNOWN.value)
            position_side = enums.PositionSide.LONG \
                if side == enums.PositionSide.LONG.value else enums.PositionSide.SHORT
            log_func = self.logger.debug
            if is_empty:
                log_func = self.logger.warning
            log_func(f"Unhandled {symbol} position mode ({position_mode.value}). This position can't be traded.")
        else:
            # One way position use BOTH side as there is always only one position per symbol.
            # This position can turn long and short
            position_side = enums.PositionSide.BOTH
        liquidation_price = fixed.get(ccxt_enums.ExchangePositionCCXTColumns.LIQUIDATION_PRICE.value, 0)
        if margin_type := fixed.get(
            ccxt_enums.ExchangePositionCCXTColumns.MARGIN_TYPE.value,
            fixed.get(ccxt_enums.ExchangePositionCCXTColumns.MARGIN_MODE.value, None)   # can also be contained in margin mode
        ):
            margin_type = enums.MarginType(margin_type)
        if force_empty or liquidation_price is None:
            liquidation_price = constants.ZERO
        else:
            liquidation_price = decimal.Decimal(str(liquidation_price))
        try:
            fixed.update({ # type: ignore
                enums.ExchangeConstantsPositionColumns.SYMBOL.value: symbol,
                enums.ExchangeConstantsPositionColumns.TIMESTAMP.value:
                    fixed.get(ccxt_enums.ExchangePositionCCXTColumns.TIMESTAMP.value,
                              self.connector.get_exchange_current_time()),
                enums.ExchangeConstantsPositionColumns.SIDE.value: position_side,
                enums.ExchangeConstantsPositionColumns.MARGIN_TYPE.value: margin_type,
                enums.ExchangeConstantsPositionColumns.SIZE.value:
                    contract_size * contracts if original_side == enums.PositionSide.LONG.value
                    else -contract_size * contracts,
                enums.ExchangeConstantsPositionColumns.CONTRACT_TYPE.value: 
                    self.connector.exchange_manager.exchange.get_contract_type(symbol),
                enums.ExchangeConstantsPositionColumns.LEVERAGE.value:
                    self.safe_decimal(fixed, ccxt_enums.ExchangePositionCCXTColumns.LEVERAGE.value,
                                      constants.DEFAULT_SYMBOL_LEVERAGE),
                enums.ExchangeConstantsPositionColumns.POSITION_MODE.value: position_mode,
                # next values are always 0 when the position empty (0 contracts)
                enums.ExchangeConstantsPositionColumns.COLLATERAL.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.COLLATERAL.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.NOTIONAL.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.NOTIONAL.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.INITIAL_MARGIN.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.INITIAL_MARGIN.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.AUTO_DEPOSIT_MARGIN.value: False,    # default value
                enums.ExchangeConstantsPositionColumns.UNREALIZED_PNL.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.UNREALISED_PNL.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.REALISED_PNL.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.REALISED_PNL.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.LIQUIDATION_PRICE.value: liquidation_price,
                enums.ExchangeConstantsPositionColumns.MARK_PRICE.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.MARK_PRICE.value, 0) or 0}"),
                enums.ExchangeConstantsPositionColumns.ENTRY_PRICE.value: constants.ZERO if is_empty else
                decimal.Decimal(
                    f"{fixed.get(ccxt_enums.ExchangePositionCCXTColumns.ENTRY_PRICE.value, 0) or 0}"),
            })
        except KeyError as e:
            self.logger.error(f"Fail to parse position dict ({e})")
        return fixed # type: ignore

    def fix_funding_rate(self, raw: CCXTFundingRate, **kwargs) -> dict:
        fixed = super().fix_funding_rate(raw, **kwargs)
        # CCXT standard funding_rate fixing logic
        return fixed

    def parse_funding_rate(self, fixed: CCXTFundingRate, from_ticker: bool = False, **kwargs) -> dict:
        # CCXT standard funding_rate parsing logic
        fixed.update({ # type: ignore
            enums.ExchangeConstantsFundingColumns.FUNDING_RATE.value:
                self.safe_decimal(
                    fixed, ccxt_enums.ExchangeFundingCCXTColumns.FUNDING_RATE.value, constants.NaN
                ),
            enums.ExchangeConstantsFundingColumns.LAST_FUNDING_TIME.value:
                self.get_uniformized_timestamp(
                    fixed.get(ccxt_enums.ExchangeFundingCCXTColumns.PREVIOUS_FUNDING_TIMESTAMP.value, 0)
                    or 0
                ),
            enums.ExchangeConstantsFundingColumns.PREDICTED_FUNDING_RATE.value:
                self.safe_decimal(
                    fixed, ccxt_enums.ExchangeFundingCCXTColumns.FUNDING_RATE.value, constants.NaN
                ),
            enums.ExchangeConstantsFundingColumns.NEXT_FUNDING_TIME.value:
                self.get_uniformized_timestamp(
                    fixed.get(ccxt_enums.ExchangeFundingCCXTColumns.FUNDING_TIMESTAMP.value, 0) or 0
                ),
        })
        return fixed # type: ignore

    def fix_leverage(self, raw: CCXTLeverage, **kwargs) -> dict:
        fixed = super().fix_leverage(raw, **kwargs)
        # CCXT standard leverage fixing logic
        return fixed

    def parse_leverage(self, fixed: CCXTLeverage, **kwargs) -> dict:
        # CCXT standard leverage fixing logic
        return fixed # type: ignore

    def fix_funding_rate_history(self, raw: CCXTFundingRates, **kwargs) -> list[dict]:
        fixed = super().fix_funding_rate_history(raw, **kwargs)
        # CCXT standard funding_rate_history fixing logic
        return fixed

    def parse_funding_rate_history(self, fixed: CCXTFundingRates, **kwargs) -> list[dict]:
        # CCXT standard funding_rate_history parsing logic
        return fixed # type: ignore

    def fix_leverage_tiers(self, raw: CCXTLeverageTiers, **kwargs) -> dict[str, list[dict]]:
        fixed = super().fix_leverage_tiers(raw, **kwargs)
        # CCXT standard leverage_tiers fixing logic
        return fixed

    def parse_leverage_tiers(self, fixed: CCXTLeverageTiers, **kwargs) -> dict[str, list[dict]]:
        # CCXT standard leverage_tiers parsing logic
        
        # {
        #   "BTC/USDT": [
        #       {
        #           ExchangeConstantsLeverageTiersColumns.TIER.value: 1.0, 
        #           ExchangeConstantsLeverageTiersColumns.CURRENCY.value: "USDT", 
        #           ExchangeConstantsLeverageTiersColumns.MIN_NOTIONAL.value: 0.0, 
        #           ExchangeConstantsLeverageTiersColumns.MAX_NOTIONAL.value: 5000.0,
        #           ExchangeConstantsLeverageTiersColumns.MAINTENANCE_MARGIN_RATE.value: 0.01, 
        #           ExchangeConstantsLeverageTiersColumns.MAX_LEVERAGE.value: 50.0, 
        #           ExchangeConstantsLeverageTiersColumns.INFO.value: {
        #               'bracket': '1', 'initialLeverage': '50', 'notionalCap': '5000',
        #               'notionalFloor': '0', 'maintMarginRatio': '0.01', 'cum': '0.0'
        #           }
        #       }
        #   ]
        # }
        for symbol, tiers in fixed.items():
            for tier_index, tier in enumerate(tiers):
                # note all typing: ignore are due to LeverageTier not extending TypedDict
                fixed[symbol][tier_index]= { # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.TIER.value:
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.TIER.value), # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.CURRENCY.value: 
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.CURRENCY.value), # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.MIN_NOTIONAL.value:
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.MIN_NOTIONAL.value), # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.MAX_NOTIONAL.value:
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.MAX_NOTIONAL.value), # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.MAINTENANCE_MARGIN_RATE.value:
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.MAINTENANCE_MARGIN_RATE.value), # type: ignore
                    enums.ExchangeConstantsLeverageTiersColumns.MAX_LEVERAGE.value:
                        tier.get(ccxt_enums.ExchangeLeverageTiersCCXTColumns.MAX_LEVERAGE.value), # type: ignore
                }
        return fixed # type: ignore

    def fix_mark_price(self, raw: dict, **kwargs) -> dict:
        fixed = super().fix_mark_price(raw, **kwargs)
        # CCXT standard mark_price fixing logic
        return fixed

    def parse_mark_price(self, fixed: dict, **kwargs) -> dict:
        # CCXT standard mark_price parsing logic
        return fixed

    def fix_market_status(self, raw: CCXTMarket, remove_price_limits: bool = False, **kwargs) -> dict:
        fixed = super().fix_market_status(raw, remove_price_limits=remove_price_limits, **kwargs)
        if not fixed:
            return fixed
        # CCXT standard market_status fixing logic
        fixed[enums.ExchangeConstantsMarketStatusColumns.PRECISION.value][
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value] = number_util.get_digits_count(
            fixed[enums.ExchangeConstantsMarketStatusColumns.PRECISION.value][
                enums.ExchangeConstantsMarketStatusColumns.PRECISION_AMOUNT.value]
        )
        fixed[enums.ExchangeConstantsMarketStatusColumns.PRECISION.value][
            enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value] = number_util.get_digits_count(
            fixed[enums.ExchangeConstantsMarketStatusColumns.PRECISION.value][
                enums.ExchangeConstantsMarketStatusColumns.PRECISION_PRICE.value]
        )
        if remove_price_limits:
            fixed[enums.ExchangeConstantsMarketStatusColumns.LIMITS.value][
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value][
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MIN.value] = None
            fixed[enums.ExchangeConstantsMarketStatusColumns.LIMITS.value][
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE.value][
                enums.ExchangeConstantsMarketStatusColumns.LIMITS_PRICE_MAX.value] = None

        return fixed

    def parse_market_status(self, fixed: CCXTMarket, remove_price_limits=False, **kwargs) -> dict:
        # CCXT standard market_status parsing logic
        return fixed # type: ignore

    def parse_transaction(self, fixed: CCXTTransaction, **kwargs) -> dict:
        # CCXT standard transaction parsing logic
        return {
            enums.ExchangeConstantsTransactionColumns.ID.value: fixed.get(enums.ExchangeConstantsTransactionColumns.ID.value),
            enums.ExchangeConstantsTransactionColumns.TXID.value: fixed.get(enums.ExchangeConstantsTransactionColumns.TXID.value),
            enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: fixed.get(enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value),
            enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value: fixed.get(enums.ExchangeConstantsTransactionColumns.ADDRESS_FROM.value),
            enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value: fixed.get(enums.ExchangeConstantsTransactionColumns.ADDRESS_TO.value),
            enums.ExchangeConstantsTransactionColumns.TAG.value: fixed.get(enums.ExchangeConstantsTransactionColumns.TAG.value),
            enums.ExchangeConstantsTransactionColumns.TYPE.value: fixed.get(enums.ExchangeConstantsTransactionColumns.TYPE.value),
            enums.ExchangeConstantsTransactionColumns.AMOUNT.value: decimal.Decimal(str(fixed.get(enums.ExchangeConstantsTransactionColumns.AMOUNT.value, 0))),
            enums.ExchangeConstantsTransactionColumns.CURRENCY.value: fixed.get(enums.ExchangeConstantsTransactionColumns.CURRENCY.value),
            enums.ExchangeConstantsTransactionColumns.STATUS.value: fixed.get(enums.ExchangeConstantsTransactionColumns.STATUS.value),
            enums.ExchangeConstantsTransactionColumns.FEE.value: fixed.get(enums.ExchangeConstantsTransactionColumns.FEE.value),
            enums.ExchangeConstantsTransactionColumns.NETWORK.value: fixed.get(enums.ExchangeConstantsTransactionColumns.NETWORK.value),
            enums.ExchangeConstantsTransactionColumns.COMMENT.value: fixed.get(enums.ExchangeConstantsTransactionColumns.COMMENT.value),
            enums.ExchangeConstantsTransactionColumns.INTERNAL.value: fixed.get(enums.ExchangeConstantsTransactionColumns.INTERNAL.value),
        }

    def parse_deposit_address(self, fixed: CCXTDepositAddress, **kwargs) -> dict:
        # CCXT standard deposit_address parsing logic
        return {
            # note all typing: ignore are due to DepositAddress not extending TypedDict
            enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value: fixed.get(enums.ExchangeConstantsDepositAddressColumns.CURRENCY.value), # type: ignore
            enums.ExchangeConstantsDepositAddressColumns.NETWORK.value: fixed.get(enums.ExchangeConstantsDepositAddressColumns.NETWORK.value), # type: ignore
            enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value: fixed.get(enums.ExchangeConstantsDepositAddressColumns.ADDRESS.value), # type: ignore
            enums.ExchangeConstantsDepositAddressColumns.TAG.value: fixed.get(enums.ExchangeConstantsDepositAddressColumns.TAG.value), # type: ignore
        }
