import contextlib
import typing
import uuid

import octobot_commons.databases as databases
import octobot_commons.tree as commons_tree
import octobot_commons.constants as common_constants
import octobot_commons.profiles as commons_profiles
import octobot_commons.logging as commons_logging
import octobot_trading.exchanges
import octobot_trading.exchange_data
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import octobot_tentacles_manager.api
import octobot.databases_util as databases_util
import tentacles.Meta.Keywords.scripting_library as scripting_library
import octobot_flow.errors
import octobot_flow.entities
import octobot_flow.repositories.exchange.exchange_repository_factory as exchange_repository_factory
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository
import octobot_flow.logic.configuration

class ExchangeContextMixin:
    WILL_EXECUTE_STRATEGY: bool = False

    def __init__(
        self,
        automation_state: octobot_flow.entities.AutomationState,
        fetched_dependencies: octobot_flow.entities.FetchedDependencies,
    ):
        self.automation_state: octobot_flow.entities.AutomationState = automation_state
        self.fetched_dependencies: octobot_flow.entities.FetchedDependencies = fetched_dependencies
        self.profile_data_provider: octobot_flow.logic.configuration.ProfileDataProvider = octobot_flow.logic.configuration.ProfileDataProvider()

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

    def init_strategy_exchange_data(self, exchange_data: exchange_data_import.ExchangeData):
        """
        should be implemented when self.WILL_EXECUTE_STRATEGY is True
        """
        raise NotImplementedError("init_strategy_exchange_data should be implemented in subclass")
    
    def ensure_context(self):
        if self._exchange_manager is None:
            raise octobot_flow.errors.ExchangeAccountInitializationError("Not in exchange context")

    @contextlib.asynccontextmanager
    async def exchange_manager_context(
        self, as_reference_account: bool
    ) -> typing.AsyncGenerator[typing.Optional[octobot_trading.exchanges.ExchangeManager], None]:
        exchange_manager_bot_id = None
        profile_data = self.profile_data_provider.get_profile_data()
        if not self.automation_state.has_exchange():
            # no need to initialize an exchange manager
            yield None
            return
        exchange_data = self.automation_state.exchange_account_details.to_minimal_exchange_data(
            self.automation_state.automation.get_exchange_account_elements(as_reference_account).portfolio.content
        )
        try:
            if self.WILL_EXECUTE_STRATEGY:
                # make all markets available to the strategy, it will use the required ones
                self.init_strategy_exchange_data(exchange_data)
            tentacles_setup_config = scripting_library.get_full_tentacles_setup_config()
            exchange_config_by_exchange = scripting_library.get_config_by_tentacle(profile_data)
            auth = profile_data.trader_simulator.enabled is False
            builder = await self._get_exchange_builder(
                profile_data,
                exchange_data,
                auth,
                tentacles_setup_config,
                exchange_config_by_exchange,
            )
            octobot_tentacles_manager.api.set_tentacle_config_proxy(scripting_library.empty_config_proxy)
            exchange_config = builder.config[common_constants.CONFIG_EXCHANGES][exchange_data.exchange_details.name]
            ignore_config = (
                not auth and not scripting_library.is_auth_required_exchanges(
                    exchange_data, tentacles_setup_config, exchange_config_by_exchange
                )
            )
            async with octobot_trading.exchanges.get_local_exchange_manager(
                exchange_data.exchange_details.name, exchange_config, tentacles_setup_config,
                exchange_data.auth_details.sandboxed, ignore_config=ignore_config,
                builder=builder, use_cached_markets=True,
                is_broker_enabled=exchange_data.auth_details.broker_enabled,
                exchange_config_by_exchange=exchange_config_by_exchange,
                disable_unauth_retry=True,  # unauth fallback is never required, if auth fails, this should fail
            ) as exchange_manager:
                exchange_manager_bot_id = exchange_manager.bot_id
                octobot_trading.exchange_data.initialize_contracts_from_exchange_data(exchange_manager, exchange_data)
                price_by_symbol = {
                    market.symbol: self.get_price_from_exchange_data_or_cached_tickers(exchange_data, market.symbol)
                    for market in exchange_data.markets
                }
                await exchange_manager.initialize_from_exchange_data(
                    exchange_data, price_by_symbol, False,
                    False, profile_data.trader_simulator.enabled
                )
                portfolio_config = {
                    asset: portfolio_element[common_constants.PORTFOLIO_TOTAL]
                    for asset, portfolio_element in exchange_data.portfolio_details.content.items()
                }
                exchange_manager.exchange_personal_data.portfolio_manager.apply_forced_portfolio(portfolio_config)
                self._exchange_manager = exchange_manager
                if self.WILL_EXECUTE_STRATEGY:
                    with self._predictive_order_sync_context(exchange_manager, profile_data):
                        yield exchange_manager
                else:
                    yield exchange_manager
        finally:
            if exchange_manager_bot_id:
                if databases.RunDatabasesProvider.instance().has_bot_id(exchange_manager_bot_id):
                    databases.RunDatabasesProvider.instance().remove_bot_id(exchange_manager_bot_id)
                commons_tree.EventProvider.instance().remove_event_tree(exchange_manager_bot_id)
            self._exchange_manager = None

    def get_exchange_config(self) -> dict:
        raise NotImplementedError("get_exchange_config not implemented")

    def get_price_from_exchange_data_or_cached_tickers(
        self, exchange_data: exchange_data_import.ExchangeData, symbol: str
    ) -> typing.Optional[float]:
        try:
            return exchange_data.get_price(symbol)
        except (IndexError, KeyError):
            try:
                price = tickers_repository.TickersRepository.get_cached_market_price(
                    exchange_data.exchange_details.name, exchange_data.auth_details.exchange_type,
                    exchange_data.auth_details.sandboxed, symbol,
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

    async def _get_exchange_builder(
        self,
        profile_data: commons_profiles.ProfileData,
        exchange_data: exchange_data_import.ExchangeData,
        auth: bool,
        tentacles_setup_config,
        exchange_config_by_exchange,
        matrix_id=None,
        ignore_symbols_in_exchange_init=False
    ) -> octobot_trading.exchanges.ExchangeBuilder:
        config = scripting_library.get_config(
            profile_data, exchange_data, tentacles_setup_config, auth, ignore_symbols_in_exchange_init, True
        )
        bot_id = str(uuid.uuid4())
        if tentacles_setup_config is not None:
            await databases.init_bot_storage(
                bot_id,
                databases_util.get_run_databases_identifier(
                    config.config,
                    tentacles_setup_config,
                    enable_storage=False,
                ),
                False
            )
        builder = octobot_trading.exchanges.ExchangeBuilder(
            config.config,
            exchange_data.exchange_details.name
        ) \
            .set_bot_id(bot_id) \
            .enable_storage(False)
        if auth:
            builder.is_real()
        else:
            builder.is_simulated()
        if matrix_id:
            builder.has_matrix(matrix_id)
        return builder

    @contextlib.contextmanager
    def _predictive_order_sync_context(self, exchange_manager, profile_data: commons_profiles.ProfileData):
        # disable portfolio fetch and available value updates as portfolio is already up-to-date
        with (
            # don't fetch portfolio update when creating/filling order
            exchange_manager.exchange_personal_data.orders_manager.disabled_order_auto_synchronization(),
            # dont fetch positions update when creating/filling order
            exchange_manager.exchange_personal_data.positions_manager.disabled_positions_update_from_order(),
        ):
            if profile_data.trader_simulator.enabled:
                # in simulated context, temporarily enable trader simulator automations
                # to update portfolio and handle orders as simulated
                previous_simulated_state = exchange_manager.trader.simulate
                exchange_manager.trader.simulate = True
                try:
                    yield
                finally:
                    exchange_manager.trader.simulate = previous_simulated_state
            else:
                yield
