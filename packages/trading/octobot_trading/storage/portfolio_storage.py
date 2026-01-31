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
import octobot_commons.authentication as authentication
import octobot_commons.databases as commons_databases
import octobot_commons.tree as commons_tree
import octobot_commons.constants as commons_constants

import octobot_trading.storage.abstract_storage as abstract_storage
import octobot_trading.storage.util as storage_util
import octobot_trading.personal_data.portfolios.history as portfolio_history
import octobot_trading.exchanges as exchanges


class PortfolioStorage(abstract_storage.AbstractStorage):
    IS_LIVE_CONSUMER = False
    IS_HISTORICAL = True
    PRICE_INIT_TIMEOUT = 30
    HISTORY_TABLE = commons_enums.RunDatabases.HISTORICAL_PORTFOLIO_VALUE.value
    IS_MULTI_EXCHANGE_STORAGE = True   # set True when this storage is updating data from all other exchanges as well

    @abstract_storage.AbstractStorage.hard_reset_and_retry_if_necessary
    async def store_history(self, reset=False):
        if not self.enabled:
            return
        portfolio_db = self.get_db()
        hist_portfolio_values_manager = self.exchange_manager.exchange_personal_data.\
            portfolio_manager.historical_portfolio_value_manager
        metadata = hist_portfolio_values_manager.get_metadata()
        # replace the whole table to ensure consistency
        history = hist_portfolio_values_manager.get_dict_historical_values()
        existing_history = await portfolio_db.all(self.HISTORY_TABLE)
        self._to_update_auth_data_ids_buffer.update(
            (
                history_val[portfolio_history.HistoricalAssetValue.TIMESTAMP_KEY]
                for history_val in history
                if history_val not in existing_history
            )
        )
        await portfolio_db.upsert(commons_enums.RunDatabases.METADATA.value, metadata, None, uuid=1)
        await portfolio_db.replace_all(
            self.HISTORY_TABLE,
            history,
            cache=False
        )
        await self.trigger_debounced_flush()
        await self.trigger_debounced_update_auth_data(reset)

    async def _update_auth_data(self, reset):
        authenticator = authentication.Authenticator.instance()
        if not authenticator.is_initialized():
            return
        current_value = 0
        initial_value_by_timestamp = {}
        reference_market = None
        ending_portfolio = {}
        price_by_asset = {}
        historical_value_by_timestamp = {}
        for exchange_manager in exchanges.Exchanges.instance().get_exchanges_managers_with_same_matrix_id(
            self.exchange_manager
        ):
            if not exchange_manager.exchange_personal_data.portfolio_manager:
                # exchange has no portfolio (probably not trading)
                continue
            hist_portfolio_values_manager = exchange_manager.exchange_personal_data. \
                portfolio_manager.historical_portfolio_value_manager
            if initializing_prices := hist_portfolio_values_manager.portfolio_manager.portfolio_value_holder.\
                value_converter.initializing_symbol_prices_pairs:
                for symbol in initializing_prices:
                    await commons_tree.EventProvider.instance().wait_for_event(
                        self.exchange_manager.bot_id,
                        commons_tree.get_exchange_path(
                            self.exchange_manager.exchange_name,
                            commons_enums.InitializationEventExchangeTopics.PRICE.value,
                            symbol=symbol,
                        ),
                        self.PRICE_INIT_TIMEOUT
                    )
            reference_market = hist_portfolio_values_manager.portfolio_manager.reference_market
            full_history = hist_portfolio_values_manager.get_dict_historical_values()
            if full_history:
                latest_value = full_history[-1]
                first_value = full_history[0]
            else:
                # use current value
                latest_value = {
                    portfolio_history.HistoricalAssetValue.VALUES_KEY: {
                        reference_market: float(
                            hist_portfolio_values_manager.portfolio_manager.portfolio_value_holder.portfolio_current_value
                        )
                    },
                    portfolio_history.HistoricalAssetValue.TIMESTAMP_KEY:
                        self.exchange_manager.exchange.get_exchange_current_time(),
                }
                first_value = latest_value
            if not (latest_value and first_value and hist_portfolio_values_manager.ending_portfolio):
                continue
            price_by_asset.update(
                hist_portfolio_values_manager.portfolio_manager.portfolio_value_holder.current_crypto_currencies_values
            )
            if hist_portfolio_values_manager.ending_portfolio:
                for asset, value in hist_portfolio_values_manager.ending_portfolio.items():
                    if asset not in ending_portfolio:
                        ending_portfolio[asset] = {
                            commons_constants.PORTFOLIO_AVAILABLE: 0,
                            commons_constants.PORTFOLIO_TOTAL: 0
                        }
                    ending_portfolio[asset][commons_constants.PORTFOLIO_AVAILABLE] += \
                        value[commons_constants.PORTFOLIO_AVAILABLE]
                    ending_portfolio[asset][commons_constants.PORTFOLIO_TOTAL] += \
                        value[commons_constants.PORTFOLIO_TOTAL]
            current_value += latest_value[portfolio_history.HistoricalAssetValue.VALUES_KEY].get(reference_market, 0)
            min_ts = first_value[portfolio_history.HistoricalAssetValue.TIMESTAMP_KEY]
            initial_value_by_timestamp[min_ts] = initial_value_by_timestamp.get(min_ts, 0) + \
                first_value[portfolio_history.HistoricalAssetValue.VALUES_KEY].get(reference_market, 0)
            history = [
                history_val
                for history_val in hist_portfolio_values_manager.get_dict_historical_values()
                if history_val[portfolio_history.HistoricalAssetValue.TIMESTAMP_KEY] in self._to_update_auth_data_ids_buffer
            ]
            if not self.exchange_manager.is_trader_simulated:
                # skip portfolio history on simulated trading
                for history_val in history:
                    ts = history_val[portfolio_history.HistoricalAssetValue.TIMESTAMP_KEY]
                    value = history_val[portfolio_history.HistoricalAssetValue.VALUES_KEY]
                    if ts in historical_value_by_timestamp:
                        for key, val in value.items():
                            if key in historical_value_by_timestamp[ts]:
                                historical_value_by_timestamp[ts][key] += val
                            else:
                                historical_value_by_timestamp[ts][key] = value
                    else:
                        historical_value_by_timestamp[ts] = value

        if current_value:
            # only consider the initial value of the min timestamp
            initial_value = initial_value_by_timestamp[min(initial_value_by_timestamp)]
            await authenticator.update_portfolio(
                {reference_market: current_value},
                {reference_market: initial_value},
                ((100 * current_value / initial_value) - 100) if initial_value else 0,
                reference_market,
                ending_portfolio,
                historical_value_by_timestamp,
                price_by_asset,
                reset
            )
            self._to_update_auth_data_ids_buffer.clear()

    def get_db(self):
        return self._get_db()

    def _get_db(self):
        return commons_databases.RunDatabasesProvider.instance().get_historical_portfolio_value_db(
            self.exchange_manager.bot_id,
            storage_util.get_account_type_suffix_from_exchange_manager(self.exchange_manager),
            self.exchange_manager.exchange_name,
        )
