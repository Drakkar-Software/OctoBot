import asyncio
import contextlib
import typing

import octobot_commons.profiles as commons_profiles
import octobot_commons.constants as common_constants
import octobot_commons.symbols as symbol_util
import octobot_commons.list_util as list_util
import octobot_commons.logging as common_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums
import octobot_trading.errors
import octobot_trading.personal_data as personal_data
import octobot_trading.exchanges
import octobot_trading.exchange_data
import octobot_trading.exchanges.util.exchange_data as exchange_data_import
import tentacles.Meta.Keywords.scripting_library as scripting_library
import octobot_flow.repositories.exchange
import octobot_flow.entities
import octobot_flow.errors

import octobot_flow.logic.exchange
import octobot_flow.logic.dsl


class ExchangeAccountJob(octobot_flow.repositories.exchange.ExchangeContextMixin):
    def __init__(
        self,
        automation_state: octobot_flow.entities.AutomationState,
        actions: list[octobot_flow.entities.AbstractActionDetails],
    ):
        super().__init__(automation_state, octobot_flow.entities.FetchedDependencies())
        self.actions: list[octobot_flow.entities.AbstractActionDetails] = actions

        self._logger: common_logging.BotLogger = common_logging.get_logger(self.__class__.__name__)
    
    async def update_public_data(self):
        """
        Fetches all public data that might be required for any bot from the exchange 
        """
        self._ensure_exchange_dependencies()
        await self._fetch_tickers()
        await self._fetch_ohlcvs()

    async def update_authenticated_data(self):
        fetched_authenticated_data = octobot_flow.entities.FetchedExchangeAccountElements()
        self._ensure_exchange_dependencies()
        await self._fetch_authenticated_data(fetched_authenticated_data)
        await self._update_bot_authenticated_data(fetched_authenticated_data)

    async def _fetch_authenticated_data(self, fetched_authenticated_data: octobot_flow.entities.FetchedExchangeAccountElements):
        coros = [
            self._fetch_open_orders(fetched_authenticated_data),
            self._fetch_portfolio(fetched_authenticated_data),
        ]
        if self._exchange_manager.is_future:
            coros.append(self._fetch_positions(fetched_authenticated_data))
        await asyncio.gather(*coros)

    async def _update_bot_authenticated_data(
        self,
        fetched_authenticated_data: octobot_flow.entities.FetchedExchangeAccountElements,
    ):
        # bind fetched data to the relevant automation account
        is_simulated = self.automation_state.exchange_account_details.is_simulated()
        if is_simulated:
            simulated_exchange_account_resolver = octobot_flow.logic.exchange.SimulatedExchangeAccountResolver(
                self.automation_state,
                self.fetched_dependencies,
                self.actions,
            )
            await simulated_exchange_account_resolver.resolve()
        else:
            # updating account with real trading data:
            target_account = self.automation_state.automation.exchange_account_elements
            if target_account is None:
                raise octobot_flow.errors.ExchangeAccountInitializationError(
                    "Exchange account elements are required to update the account"
                )
            target_account.orders = fetched_authenticated_data.orders
            target_account.positions = fetched_authenticated_data.positions
            sub_portfolio_resolver = octobot_flow.logic.exchange.SubPortfolioResolver(
                self.automation_state
            )
            await sub_portfolio_resolver.resolve()

    async def _create_exchange_producers(self, exchange_manager):
        await octobot_trading.exchanges.create_exchange_channels(exchange_manager)
        await octobot_trading.exchanges.create_producers(
            exchange_manager, 
            octobot_trading.exchange_data.UNAUTHENTICATED_UPDATER_PRODUCERS,
            start_producers=False,
            subscribe_indirect_producers_if_not_started=False
        )
        if not self.profile_data_provider.get_profile_data().trader_simulator.enabled:
            await octobot_trading.exchanges.create_producers(
                self._exchange_manager,
                personal_data.AUTHENTICATED_UPDATER_PRODUCERS,
                start_producers=False,
                subscribe_indirect_producers_if_not_started=False
            )

    @contextlib.asynccontextmanager
    async def account_exchange_context(self, global_profile_data: commons_profiles.ProfileData):
        with self.profile_data_provider.profile_data_context(global_profile_data):
            async with self.exchange_manager_context() as exchange_manager:
                await self._create_exchange_producers(exchange_manager)
                yield

    async def _fetch_and_save_ohlcv(
        self, repository: octobot_flow.repositories.exchange.OhlcvRepository, 
        symbol: str, time_frame: str, limit: int, tickers: dict[str, dict[str, typing.Any]]
    ):
        market = await repository.fetch_ohlcv(symbol, time_frame, limit, tickers)
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] OHLCV for {symbol} {time_frame}: ({len(market.close)} candles)"
        )
        self.fetched_dependencies.fetched_exchange_data.public_data.markets.append(market)

    async def _fetch_ohlcvs(self):
        repository = self.get_exchange_repository_factory().get_ohlcv_repository()
        history_size = scripting_library.get_required_candles_count(
            self.profile_data_provider.get_profile_data(), trading_constants.MIN_CANDLES_HISTORY_SIZE
        )
        symbols = self._get_traded_symbols()
        time_frames = self._get_time_frames()
        await asyncio.gather(*[
            self._fetch_and_save_ohlcv(
                repository, symbol, time_frame, history_size,
                self.fetched_dependencies.fetched_exchange_data.public_data.tickers
            )
            for symbol in symbols
            for time_frame in time_frames
        ])


    async def _fetch_tickers(self):
        repository = self.get_exchange_repository_factory().get_tickers_repository()
        self.fetched_dependencies.fetched_exchange_data.public_data.tickers = await repository.fetch_tickers(
            self._get_traded_symbols()
        )
        ticker_close_by_symbols = {
            symbol: ticker[octobot_trading.enums.ExchangeConstantsTickersColumns.CLOSE.value] 
            for symbol, ticker in self.fetched_dependencies.fetched_exchange_data.public_data.tickers.items()
        }
        logged_tickers = f" tickers: {ticker_close_by_symbols}" if len(ticker_close_by_symbols) < 10 else ""
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] {len(self.fetched_dependencies.fetched_exchange_data.public_data.tickers)}{logged_tickers}"
        )

    async def _fetch_positions(self, fetched_authenticated_data: octobot_flow.entities.FetchedExchangeAccountElements):
        repository = self.get_exchange_repository_factory().get_positions_repository()
        fetched_authenticated_data.positions = await repository.fetch_positions(self._get_traded_symbols())
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] {len(fetched_authenticated_data.positions)} positions: "
            f"{[position.position for position in fetched_authenticated_data.positions]}"
        )

    async def _fetch_open_orders(self, fetched_authenticated_data: octobot_flow.entities.FetchedExchangeAccountElements):
        repository = self.get_exchange_repository_factory().get_orders_repository()
        symbols = self._get_traded_symbols()
        try:
            open_orders = await repository.fetch_open_orders(symbols)
        except octobot_trading.errors.NotSupported as err:
            self._logger.info(f"Fetching open orders is not supported: {err}.")
            open_orders = []
        account_elements = self.automation_state.automation.exchange_account_elements
        previous_open_orders = (
            account_elements.orders.open_orders if account_elements is not None else []
        )
        fetched_authenticated_data.orders.open_orders = repository.update_enriched_orders(
            open_orders,
            previous_open_orders
        )
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] "
            f"{personal_data.get_symbol_count(open_orders) or "0"} open orders for {symbols}"
        )

    async def _fetch_portfolio(self, fetched_authenticated_data: octobot_flow.entities.FetchedExchangeAccountElements):
        repository_factory = self.get_exchange_repository_factory()
        repository = repository_factory.get_portfolio_repository()
        try:
            fetched_authenticated_data.portfolio.full_content = await repository.fetch_portfolio()  # type: ignore
        except octobot_trading.errors.NotSupported as err:
            self._logger.info(f"Fetching portfolio is not supported: {err}. Diabling portfolio validations.")
            fetched_authenticated_data.portfolio.full_content = {}
        balance_summary = common_logging.get_private_placeholder_if_necessary(
            personal_data.get_balance_summary(fetched_authenticated_data.portfolio.full_content, use_exchange_format=False)
        )
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] full "
            f"[{'simulated' if repository_factory.is_simulated else 'real'}] portfolio: "
            f"{balance_summary}"
        )
        self._update_exchange_account_portfolio(fetched_authenticated_data.portfolio)

    def _update_exchange_account_portfolio(self, portfolio: exchange_data_import.PortfolioDetails):
        unit = scripting_library.get_default_exchange_reference_market(self._exchange_manager.exchange_name)
        self.automation_state.exchange_account_details.portfolio.content = [
            octobot_flow.entities.PortfolioAssetHolding(
                asset,
                float(values[common_constants.PORTFOLIO_AVAILABLE]),
                float(values[common_constants.PORTFOLIO_TOTAL]),
                value=float(
                    (
                        self.fetched_dependencies.fetched_exchange_data.get_last_price(
                            symbol_util.merge_currencies(asset, unit)
                        ) if asset != unit else trading_constants.ONE
                     ) * values[common_constants.PORTFOLIO_TOTAL] # type: ignore
                ),
            )
            for asset, values in portfolio.full_content.items()
        ]

    def _get_traded_symbols(self) -> list[str]:
        profile_data = self.profile_data_provider.get_profile_data()
        config_symbols = scripting_library.get_traded_symbols(profile_data)
        return list_util.deduplicate(
            config_symbols + self.get_all_actions_symbols(profile_data)
        )

    def get_all_actions_symbols(self, profile_data: commons_profiles.ProfileData) -> list[str]:
        return octobot_flow.logic.dsl.get_actions_symbol_dependencies(
            self.actions, profile_data
        )

    def _get_time_frames(self) -> list[str]:
        return scripting_library.get_time_frames(self.profile_data_provider.get_profile_data())

    def _ensure_exchange_dependencies(self):
        if not self.fetched_dependencies.fetched_exchange_data:
            self.fetched_dependencies.fetched_exchange_data = octobot_flow.entities.FetchedExchangeData()
