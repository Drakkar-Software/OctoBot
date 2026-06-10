import contextlib
import typing

import octobot_commons.constants as common_constants
import octobot_commons.profiles as commons_profiles
import octobot_commons.logging as commons_logging
import octobot_trading.api
import octobot_trading.exchanges
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_tentacles_manager.api
import octobot_evaluators.api as evaluators_api
import octobot_flow.errors
import octobot_flow.entities
import octobot_flow.repositories.exchange.exchange_repository_factory as exchange_repository_factory
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository
import octobot_flow.logic.configuration


class ExchangeContextMixin:
    USE_PREDICTIVE_ORDERS_SYNC: bool = False

    def __init__(
        self,
        automation_state: octobot_flow.entities.AutomationState,
        fetched_dependencies: octobot_flow.entities.FetchedDependencies,
        enable_order_fill_events: bool = False,
    ):
        self.automation_state: octobot_flow.entities.AutomationState = automation_state
        self.fetched_dependencies: octobot_flow.entities.FetchedDependencies = fetched_dependencies
        self.profile_data_provider: octobot_flow.logic.configuration.ProfileDataProvider = octobot_flow.logic.configuration.ProfileDataProvider()
        self.enable_order_fill_events: bool = enable_order_fill_events

        # context dependant attributes
        self._exchange_manager: typing.Optional[octobot_trading.exchanges.ExchangeManager] = None

    def get_exchange_repository_factory(self) -> exchange_repository_factory.ExchangeRepositoryFactory:
        self.ensure_context()
        return exchange_repository_factory.ExchangeRepositoryFactory(
            self._exchange_manager,
            [self.automation_state.automation],
            self.fetched_dependencies.fetched_exchange_data,
            self.profile_data_provider.get_profile_data().trader_simulator.enabled,
        )

    def set_fetched_dependencies(self, fetched_dependencies: octobot_flow.entities.FetchedDependencies):
        self.fetched_dependencies = fetched_dependencies

    def init_predictive_orders_exchange_data(self, exchange_data: exchange_data_import.ExchangeData):
        """
        should be implemented when self.USE_PREDICTIVE_ORDERS_SYNC is True
        """
        raise NotImplementedError("init_predictive_orders_exchange_data should be implemented in subclass")
    
    def ensure_context(self):
        if self._exchange_manager is None:
            raise octobot_flow.errors.ExchangeAccountInitializationError("Not in exchange context")

    @contextlib.asynccontextmanager
    async def exchange_manager_context(
        self,
    ) -> typing.AsyncGenerator[typing.Optional[octobot_trading.exchanges.ExchangeManager], None]:
        profile_data = self.profile_data_provider.get_profile_data()
        if not self.automation_state.has_exchange():
            # no need to initialize an exchange manager
            yield None
            return
        automation_elements = self.automation_state.automation.exchange_account_elements
        portfolio_content = (
            automation_elements.portfolio.content
            if automation_elements is not None
            else {}
        )
        exchange_data = self.automation_state.exchange_account_details.to_minimal_exchange_data(
            portfolio_content
        )
        if self.fetched_dependencies.fetched_exchange_data:
            exchange_data.markets = self.fetched_dependencies.fetched_exchange_data.public_data.markets
        matrix_id = None
        try:
            matrix_id = evaluators_api.create_matrix()
            if self.USE_PREDICTIVE_ORDERS_SYNC:
                # make all markets available to the strategy, it will use the required ones
                self.init_predictive_orders_exchange_data(exchange_data)
            tentacles_setup_config = octobot_tentacles_manager.api.get_full_tentacles_setup_config()
            async with octobot_trading.exchanges.exchange_manager_from_exchange_data(
                exchange_data,
                profile_data,
                tentacles_setup_config,
                price_fallback=self._get_price_from_cached_tickers,
                matrix_id=matrix_id,
            ) as exchange_manager:
                portfolio_config = {
                    asset: portfolio_element[common_constants.PORTFOLIO_TOTAL]
                    for asset, portfolio_element in exchange_data.portfolio_details.content.items()
                }
                portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager
                portfolio_manager.apply_forced_portfolio(
                    portfolio_config,
                    # lock open orders funds in portfolio for simulated trading
                    update_available_funds_from_open_orders=profile_data.trader_simulator.enabled,
                )
                self._exchange_manager = exchange_manager
                if self.USE_PREDICTIVE_ORDERS_SYNC:
                    async with self._predictive_order_sync_context(
                        exchange_manager, profile_data
                    ):
                        yield exchange_manager
                else:
                    yield exchange_manager
        finally:
            if matrix_id is not None:
                evaluators_api.del_matrix(matrix_id)
            self._exchange_manager = None

    def get_exchange_config(self) -> dict:
        raise NotImplementedError("get_exchange_config not implemented")

    def _get_price_from_cached_tickers(
        self, exchange_data: exchange_data_import.ExchangeData, symbol: str
    ) -> typing.Optional[float]:
        try:
            price = tickers_repository.TickersRepository.get_cached_market_price_from_exchange_data(
                exchange_data, symbol
            )
            commons_logging.get_logger(self.__class__.__name__).warning(
                f"Using {symbol} [{exchange_data.exchange_details.name}] "
                f"ticker price for mark price: candles are missing"
            )
            return price
        except KeyError:
            commons_logging.get_logger(self.__class__.__name__).error(
                f"Impossible to initialize {symbol} price on {exchange_data.exchange_details.name}: no "
                f"candle or cached ticker price"
            )
        return None

    @contextlib.asynccontextmanager
    async def _predictive_order_sync_context(
        self,
        exchange_manager,
        profile_data: commons_profiles.ProfileData,
    ):
        # disable portfolio fetch and available value updates as portfolio is already up-to-date
        with (
            # don't fetch portfolio update when creating/filling order
            exchange_manager.exchange_personal_data.orders_manager.disabled_order_auto_synchronization(
                enable_order_fill_events=self.enable_order_fill_events
            ),
            # dont fetch positions update when creating/filling order
            exchange_manager.exchange_personal_data.positions_manager.disabled_positions_update_from_order(),
        ):
            if profile_data.trader_simulator.enabled:
                if self.enable_order_fill_events:
                    # initialize order fill events
                    for order in octobot_trading.api.get_open_orders(exchange_manager):
                        await order.update_order_status()
                # in simulated context, temporarily enable trader simulator automations
                # to update portfolio and handle orders as simulated
                previous_simulated_state = exchange_manager.trader.simulate
                exchange_manager.trader.simulate = True
                exchange_manager.exchange_personal_data.error_on_channel_notification_push_error = not self.enable_order_fill_events
                try:
                    yield
                finally:
                    exchange_manager.trader.simulate = previous_simulated_state
                    exchange_manager.exchange_personal_data.error_on_channel_notification_push_error = False
            else:
                yield
