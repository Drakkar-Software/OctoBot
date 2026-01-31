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
import octobot_commons.enums as commons_enums
import octobot_commons.databases as commons_databases

import octobot_trading.storage.abstract_storage as abstract_storage
import octobot_trading.storage.util as storage_util


class TransactionsStorage(abstract_storage.AbstractStorage):
    IS_LIVE_CONSUMER = False
    HISTORY_TABLE = commons_enums.DBTables.TRANSACTIONS.value

    @abstract_storage.AbstractStorage.hard_reset_and_retry_if_necessary
    async def _store_history(self):
        transactions = [
            transaction
            for transaction in self.exchange_manager.exchange_personal_data.transactions_manager.transactions.values()
        ]
        y_data = self.plot_settings.y_data or [0] * len(transactions)
        await self._get_db().replace_all(
            self.HISTORY_TABLE,
            [
                _format_transaction(
                    transaction,
                    self.exchange_manager,
                    self.plot_settings.chart,
                    self.plot_settings.x_multiplier,
                    self.plot_settings.kind,
                    self.plot_settings.mode,
                    y_data[index]
                )
                for index, transaction in enumerate(transactions)
            ],
            cache=False,
        )
        await self.trigger_debounced_flush()

    def _get_db(self):
        return commons_databases.RunDatabasesProvider.instance().get_transactions_db(
            self.exchange_manager.bot_id,
            storage_util.get_account_type_suffix_from_exchange_manager(self.exchange_manager),
            self.exchange_manager.exchange_name
        )


def _format_transaction(transaction, exchange_manager, chart, x_multiplier, kind, mode, y_data):
    return {
        commons_enums.DisplayedElementTypes.CHART.value: chart,
        commons_enums.DBRows.SYMBOL.value: transaction.symbol,
        commons_enums.PlotAttributes.X.value: transaction.creation_time * x_multiplier,
        commons_enums.PlotAttributes.TYPE.value: transaction.transaction_type.value,
        commons_enums.PlotAttributes.SIDE.value: transaction.side.value if hasattr(transaction, "side") else None,
        commons_enums.PlotAttributes.Y.value: y_data,
        commons_enums.PlotAttributes.KIND.value: kind,
        commons_enums.PlotAttributes.MODE.value: mode,
        "id": transaction.transaction_id,
        "trading_mode": exchange_manager.trading_modes[0].get_name(),
        "currency": transaction.currency,
        "quantity": float(transaction.quantity) if hasattr(transaction, "quantity") else None,
        "order_id": transaction.order_id if hasattr(transaction, "order_id") else None,
        "funding_rate": float(transaction.funding_rate) if hasattr(transaction, "funding_rate") else None,
        "realised_pnl": float(transaction.realised_pnl) if hasattr(transaction, "realised_pnl") else None,
        "transaction_fee": float(transaction.transaction_fee) if hasattr(transaction, "transaction_fee") else None,
        "closed_quantity": float(transaction.closed_quantity) if hasattr(transaction, "closed_quantity") else None,
        "cumulated_closed_quantity": float(transaction.cumulated_closed_quantity)
        if hasattr(transaction, "cumulated_closed_quantity") else None,
        "first_entry_time": float(transaction.first_entry_time) * x_multiplier
        if hasattr(transaction, "first_entry_time") else None,
        "average_entry_price": float(transaction.average_entry_price)
        if hasattr(transaction, "average_entry_price") else None,
        "average_exit_price": float(transaction.average_exit_price)
        if hasattr(transaction, "average_exit_price") else None,
        "order_exit_price": float(transaction.order_exit_price)
        if hasattr(transaction, "order_exit_price") else None,
        "leverage": float(transaction.leverage) if hasattr(transaction, "leverage") else None,
        "trigger_source": transaction.trigger_source.value if hasattr(transaction, "trigger_source") else None,
    }
