import decimal
import typing

import octobot_commons.asyncio_tools as asyncio_tools
import octobot_commons.logging as commons_logging
import octobot_commons.profiles as commons_profiles

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_import

import octobot_flow.entities as entities_import
import octobot_flow.errors as flow_errors
import octobot_flow.logic.configuration as configuration_import
import octobot_flow.logic.dsl as dsl_import
import octobot_flow.repositories.exchange.exchange_context_mixin as exchange_context_mixin_import
from octobot_trading.personal_data.orders import orders_manager

logger = commons_logging.get_logger(__name__)

_MARK_PRICE_UPDATE_CYCLES = 3


class _SimulatedResolutionExchangeContext(exchange_context_mixin_import.ExchangeContextMixin):
    WILL_EXECUTE_STRATEGY: bool = True

    def __init__(
        self,
        automation_state: entities_import.AutomationState,
        fetched_dependencies: entities_import.FetchedDependencies,
        as_reference_account: bool,
    ):
        super().__init__(automation_state, fetched_dependencies)
        self._resolution_as_reference_account: bool = as_reference_account

    def init_strategy_exchange_data(self, exchange_data: exchange_data_import.ExchangeData) -> None:
        exchange_account_elements = self.automation_state.automation.get_exchange_account_elements(
            self._resolution_as_reference_account
        )
        if exchange_account_elements is None:
            return
        fetched_exchange_data = self.fetched_dependencies.fetched_exchange_data
        if fetched_exchange_data is not None:
            exchange_data.markets = fetched_exchange_data.public_data.markets
        exchange_data.portfolio_details.content = exchange_account_elements.portfolio.content
        exchange_data.orders_details.open_orders = list(exchange_account_elements.orders.open_orders)
        exchange_data.orders_details.missing_orders = list(exchange_account_elements.orders.missing_orders)
        exchange_data.positions = list(exchange_account_elements.positions)


class SimulatedExchangeAccountResolver:
    def __init__(
        self,
        automation_state: entities_import.AutomationState,
        fetched_dependencies: entities_import.FetchedDependencies,
        actions: list[entities_import.AbstractActionDetails],
        as_reference_account: bool,
    ):
        self._simulation_exchange_context: _SimulatedResolutionExchangeContext = _SimulatedResolutionExchangeContext(
            automation_state, fetched_dependencies, as_reference_account
        )
        self._actions: list[entities_import.AbstractActionDetails] = actions
        self._as_reference_account: bool = as_reference_account

    def _get_profile_data(self) -> commons_profiles.ProfileData:
        minimal_profile_data = configuration_import.create_profile_data(
            self._simulation_exchange_context.automation_state.exchange_account_details,
            self._simulation_exchange_context.automation_state.automation.metadata.automation_id,
            set(),
        )
        return configuration_import.create_profile_data(
            self._simulation_exchange_context.automation_state.exchange_account_details,
            self._simulation_exchange_context.automation_state.automation.metadata.automation_id,
            set(dsl_import.get_actions_symbol_dependencies(self._actions, minimal_profile_data)),
        )

    async def resolve(self) -> None:
        account_elements = self._simulation_exchange_context.automation_state.automation.get_exchange_account_elements(
            self._as_reference_account
        )
        if account_elements is None:
            logger.debug(
                "SimulatedExchangeAccountResolver: no exchange account elements for "
                f"as_reference_account={self._as_reference_account}, skipping"
            )
            return

        if not account_elements.orders.open_orders and not account_elements.positions:
            logger.debug(
                "SimulatedExchangeAccountResolver: no open orders and no positions on account elements, skipping"
            )
            return

        with self._simulation_exchange_context.profile_data_provider.profile_data_context(
            self._get_profile_data()
        ):
            async with self._simulation_exchange_context.exchange_manager_context(self._as_reference_account) as simulated_exchange_manager:
                if simulated_exchange_manager is None:
                    raise flow_errors.ExchangeAccountInitializationError(
                        "Simulated exchange manager was not initialized inside exchange_manager_context"
                    )

                # tmp
                simulated_exchange_manager.exchange_personal_data.orders_manager.enable_order_auto_synchronization = True
                for order in simulated_exchange_manager.exchange_personal_data.orders_manager.orders.values():
                    await order.update_order_status()
                # eend tmp
                fetched_exchange_data = self._simulation_exchange_context.fetched_dependencies.fetched_exchange_data
                if fetched_exchange_data is None:
                    raise flow_errors.ExchangeAccountInitializationError(
                        "SimulatedExchangeAccountResolver: fetched exchange data is not initialized"
                    )
                # fetched_exchange_data.authenticated_data.sync_from_exchange_manager(simulated_exchange_manager)

                self._push_mark_prices_from_fetched_tickers(simulated_exchange_manager, account_elements, fetched_exchange_data)
                for _ in range(_MARK_PRICE_UPDATE_CYCLES):
                    await asyncio_tools.wait_asyncio_next_cycle()

                account_elements.sync_from_exchange_manager(simulated_exchange_manager)
                fetched_exchange_data.authenticated_data.sync_from_exchange_manager(
                    simulated_exchange_manager
                )

    def _push_mark_prices_from_fetched_tickers(
        self,
        simulated_exchange_manager: trading_exchanges.ExchangeManager,
        account_elements: typing.Any,
        fetched_exchange_data: entities_import.FetchedExchangeData,
    ) -> None:
        symbols = self._symbols_for_mark_price_updates(account_elements.orders.open_orders)
        for symbol in symbols:
            ticker = fetched_exchange_data.public_data.tickers.get(symbol)
            if not ticker:
                logger.error(
                    "SimulatedExchangeAccountResolver: no ticker for %s, skip mark price (simulated fills may miss)",
                    symbol,
                )
                continue
            if close_price := ticker.get(trading_enums.ExchangeConstantsTickersColumns.CLOSE.value):
                simulated_exchange_manager.get_symbol_data(symbol).handle_mark_price_update(
                    decimal.Decimal(str(close_price)),
                    trading_enums.MarkPriceSources.TICKER_CLOSE_PRICE.value,
                    reset_mark_price_from_other_sources=True
                )
            else:
                logger.error(
                    "SimulatedExchangeAccountResolver: ticker for %s has no close, skip mark price",
                    symbol,
                )

    def _symbols_for_mark_price_updates(self, open_orders: list[dict]) -> list[str]:
        symbols: set[str] = set()
        for order in open_orders:
            storage = order.get(trading_constants.STORAGE_ORIGIN_VALUE, order)
            symbol = storage.get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value)
            if symbol:
                symbols.add(symbol)
        return list(symbols)
