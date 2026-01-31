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
#  License along with this library
import octobot_commons.channels_name as channels_name
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_commons.databases as commons_databases
import octobot_commons.symbols as commons_symbols

import octobot_trading.enums as enums
import octobot_trading.errors as errors
import octobot_trading.constants as constants
import octobot_trading.storage.abstract_storage as abstract_storage
import octobot_trading.storage.util as storage_util


class TradesStorage(abstract_storage.AbstractStorage):
    LIVE_CHANNEL = channels_name.OctoBotTradingChannelsName.TRADES_CHANNEL.value
    HISTORY_TABLE = commons_enums.DBTables.TRADES.value

    @abstract_storage.AbstractStorage.hard_reset_and_retry_if_necessary
    async def _live_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        trade: dict,
        old_trade: bool
    ):
        if trade[enums.ExchangeConstantsOrderColumns.STATUS.value] != enums.OrderStatus.CANCELED.value:
            await self._get_db().log(
                self.HISTORY_TABLE,
                _format_trade(
                    trade,
                    self.exchange_manager,
                    self.plot_settings.chart,
                    self.plot_settings.x_multiplier,
                    self.plot_settings.kind,
                    self.plot_settings.mode
                )
            )
            await self.trigger_debounced_flush()
            self._to_update_auth_data_ids_buffer.add(trade[enums.ExchangeConstantsOrderColumns.ID.value])
            await self.trigger_debounced_update_auth_data(False)

    async def _update_auth_data(self, reset):
        # skip trades history on simulated trading
        if self.exchange_manager.is_trader_simulated:
            return
        authenticator = authentication.Authenticator.instance()
        history = [
            self._get_trade_dict_with_usd_like_volume(trade)
            for trade in self.exchange_manager.exchange_personal_data.trades_manager.trades.values()
            if trade.status is not enums.OrderStatus.CANCELED
            and trade.is_from_this_octobot
            and trade.trade_id in self._to_update_auth_data_ids_buffer
        ]
        if (history or reset) and authenticator.is_initialized():
            # also update when history is empty to reset trade history
            await authenticator.update_trades(history, self.exchange_manager.exchange_name, reset)
            self._to_update_auth_data_ids_buffer.clear()

    @abstract_storage.AbstractStorage.hard_reset_and_retry_if_necessary
    async def _store_history(self):
        database = self._get_db()
        await database.replace_all(
            self.HISTORY_TABLE,
            [
                _format_trade(
                    trade.to_dict(),
                    self.exchange_manager,
                    self.plot_settings.chart,
                    self.plot_settings.x_multiplier,
                    self.plot_settings.kind,
                    self.plot_settings.mode
                )
                for trade in self.exchange_manager.exchange_personal_data.trades_manager.trades.values()
                if trade.status is not enums.OrderStatus.CANCELED
            ],
            cache=False,
        )
        await database.flush()

    def _get_trade_dict_with_usd_like_volume(self, trade) -> dict:
        trade_dict = trade.to_dict()
        parsed_symbol = commons_symbols.parse_symbol(trade.symbol)
        cost_currency = parsed_symbol.quote if parsed_symbol.is_linear() else parsed_symbol.base
        try:
            usd_volume = self.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.\
                value_converter.get_usd_like_value(cost_currency, trade.total_cost)
        except errors.MissingPriceDataError:
            # can't evaluate USD-like volume
            usd_volume = constants.ZERO
        trade_dict[enums.ExchangeConstantsOrderColumns.VOLUME.value] = usd_volume
        return trade_dict

    def _get_db(self):
        return commons_databases.RunDatabasesProvider.instance().get_trades_db(
            self.exchange_manager.bot_id,
            storage_util.get_account_type_suffix_from_exchange_manager(self.exchange_manager),
            self.exchange_manager.exchange_name,
        )


def _format_trade(trade_dict, exchange_manager, chart, x_multiplier, kind, mode):
    tag = f"{trade_dict[enums.ExchangeConstantsOrderColumns.TAG.value]} " \
        if trade_dict[enums.ExchangeConstantsOrderColumns.TAG.value] else ""
    symbol = trade_dict[enums.ExchangeConstantsOrderColumns.SYMBOL.value]
    trade_side = trade_dict[enums.ExchangeConstantsOrderColumns.SIDE.value]
    is_using_positions = False
    color = shape = None
    if exchange_manager.is_future:
        positions = exchange_manager.exchange_personal_data.positions_manager.get_symbol_positions(symbol=symbol)
        if positions:
            is_using_positions = True
            # trading_side = next(iter(positions)).side
            # if trading_side is enums.PositionSide.LONG:
            if "stop_loss" in trade_dict[enums.ExchangeConstantsOrderColumns.TYPE.value]:
                shape = "x"
                color = "orange"
            elif trade_dict[enums.ExchangeConstantsOrderColumns.REDUCE_ONLY.value] is True:
                if trade_side == enums.TradeOrderSide.SELL.value:
                    # long tp
                    color = "magenta"
                    shape = "arrow-bar-left"
                else:
                    # short tp
                    color = "blue"
                    shape = "arrow-bar-left"
            else:
                if trade_side == enums.TradeOrderSide.BUY.value:
                    # long entry
                    color = "green"
                    shape = "arrow-bar-right"
                else:
                    # short entry
                    color = "red"
                    shape = "arrow-bar-right"

    if not is_using_positions:
        if trade_side == enums.TradeOrderSide.BUY.value:
            color = "blue"
            shape = "arrow-bar-right"
        elif "stop_loss" in trade_dict[enums.ExchangeConstantsOrderColumns.TYPE.value]:
            color = "orange"
            shape = "x"
        else:
            color = "magenta"
            shape = "arrow-bar-left"
    fee = trade_dict[enums.ExchangeConstantsOrderColumns.FEE.value]
    fee_cost = float(fee[enums.FeePropertyColumns.COST.value] if
                     fee and fee[enums.FeePropertyColumns.COST.value] else 0)
    return {
        constants.STORAGE_ORIGIN_VALUE: TradesStorage.sanitize_for_storage(trade_dict),
        commons_enums.DisplayedElementTypes.CHART.value: chart,
        commons_enums.DBRows.SYMBOL.value: trade_dict[enums.ExchangeConstantsOrderColumns.SYMBOL.value],
        commons_enums.DBRows.FEES_AMOUNT.value: fee_cost,
        commons_enums.DBRows.FEES_CURRENCY.value: fee[enums.FeePropertyColumns.CURRENCY.value]
        if trade_dict[enums.ExchangeConstantsOrderColumns.FEE.value] else "",
        commons_enums.DBRows.ID.value: trade_dict[enums.ExchangeConstantsOrderColumns.ID.value],
        commons_enums.DBRows.TRADING_MODE.value: exchange_manager.trading_modes[0].get_name()
        if exchange_manager.trading_modes else None,
        commons_enums.PlotAttributes.X.value: trade_dict[enums.ExchangeConstantsOrderColumns.TIMESTAMP.value] * x_multiplier,
        commons_enums.PlotAttributes.TEXT.value: f"{tag}{trade_dict[enums.ExchangeConstantsOrderColumns.TYPE.value]} "
                f"{trade_dict[enums.ExchangeConstantsOrderColumns.SIDE.value]} "
                f"{trade_dict[enums.ExchangeConstantsOrderColumns.AMOUNT.value]} "
                f"{trade_dict[enums.ExchangeConstantsOrderColumns.QUANTITY_CURRENCY.value]} "
                f"at {trade_dict[enums.ExchangeConstantsOrderColumns.PRICE.value]}",
        commons_enums.PlotAttributes.TYPE.value: trade_dict[enums.ExchangeConstantsOrderColumns.TYPE.value],
        commons_enums.PlotAttributes.VOLUME.value: float(trade_dict[enums.ExchangeConstantsOrderColumns.AMOUNT.value]),
        commons_enums.PlotAttributes.Y.value: float(trade_dict[enums.ExchangeConstantsOrderColumns.PRICE.value]),
        commons_enums.PlotAttributes.KIND.value: kind,
        commons_enums.PlotAttributes.SIDE.value: trade_dict[enums.ExchangeConstantsOrderColumns.SIDE.value],
        commons_enums.PlotAttributes.MODE.value: mode,
        commons_enums.PlotAttributes.SHAPE.value: shape,
        commons_enums.PlotAttributes.COLOR.value: color,
        commons_enums.PlotAttributes.SIZE.value: "10",
        "cost": float(trade_dict[enums.ExchangeConstantsOrderColumns.COST.value]),
        "state": trade_dict[enums.ExchangeConstantsOrderColumns.STATUS.value],
    }
