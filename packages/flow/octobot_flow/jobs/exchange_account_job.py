import asyncio
import contextlib

import octobot_commons.profiles as commons_profiles
import octobot_commons.constants as common_constants
import octobot_commons.symbols as symbol_util
import octobot_commons.list_util as list_util
import octobot_commons.logging as common_logging
import octobot_trading.constants as trading_constants
import octobot_trading.enums
import octobot_trading.personal_data as personal_data
import tentacles.Meta.Keywords.scripting_library as scripting_library
import octobot_flow.repositories.exchange
import octobot_flow.entities

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
        await asyncio.gather(
            self._fetch_ohlcvs(),
            self._fetch_tickers()
        )

    async def update_authenticated_data(self):
        self._ensure_exchange_dependencies()
        await self._fetch_authenticated_data()
        await self._update_bot_authenticated_data()
        
    async def _fetch_authenticated_data(self):
        coros = [
            self._fetch_open_orders(),
            self._fetch_portfolio(),
        ]
        if self._exchange_manager.is_future:
            coros.append(self._fetch_positions())
        await asyncio.gather(*coros)

    async def _update_bot_authenticated_data(self):
        sub_portfolio_resolver = octobot_flow.logic.exchange.SubPortfolioResolver(
            self.automation_state
        )
        await sub_portfolio_resolver.resolve_sub_portfolios()

    @contextlib.asynccontextmanager
    async def account_exchange_context(self, global_profile_data: commons_profiles.ProfileData):
        with self.profile_data_provider.profile_data_context(global_profile_data):
            async with self.exchange_manager_context(as_reference_account=False):
                yield

    async def _fetch_and_save_ohlcv(
        self, repository: octobot_flow.repositories.exchange.OhlcvRepository, 
        symbol: str, time_frame: str, limit: int
    ):
        market = await repository.fetch_ohlcv(symbol, time_frame, limit)
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] OHLCV for {symbol} {time_frame}: ({len(market.close)} candles)"
        )
        self.fetched_dependencies.fetched_exchange_data.public_data.markets.append(market)

    async def _fetch_ohlcvs(self):
        repository = self.get_exchange_repository_factory().get_ohlcv_repository()
        history_size = scripting_library.get_required_candles_count(
            self.profile_data_provider.get_profile_data(), trading_constants.MIN_CANDLES_HISTORY_SIZE
        )
        await asyncio.gather(*[
            self._fetch_and_save_ohlcv(repository, symbol, time_frame, history_size)
            for symbol in self._get_traded_symbols()
            for time_frame in self._get_time_frames()
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
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] {len(self.fetched_dependencies.fetched_exchange_data.public_data.tickers)} "
            f"tickers: {ticker_close_by_symbols}"
        )

    async def _fetch_positions(self):
        repository = self.get_exchange_repository_factory().get_positions_repository()
        self.fetched_dependencies.fetched_exchange_data.authenticated_data.positions = await repository.fetch_positions(self._get_traded_symbols())
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] {len(self.fetched_dependencies.fetched_exchange_data.authenticated_data.positions)} positions: "
            f"{[position.position for position in self.fetched_dependencies.fetched_exchange_data.authenticated_data.positions]}"
        )

    async def _fetch_open_orders(self):
        repository = self.get_exchange_repository_factory().get_orders_repository()
        symbols = self._get_traded_symbols()
        self.fetched_dependencies.fetched_exchange_data.authenticated_data.orders.open_orders = await repository.fetch_open_orders(symbols)
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] "
            f"{personal_data.get_symbol_count(self.fetched_dependencies.fetched_exchange_data.authenticated_data.orders.open_orders) or "0"} "
            f"open orders for {symbols}"
        )
    

    async def _fetch_portfolio(self):
        repository = self.get_exchange_repository_factory().get_portfolio_repository()
        self.fetched_dependencies.fetched_exchange_data.authenticated_data.portfolio.full_content = await repository.fetch_portfolio() # type: ignore
        self._logger.info(
            f"Fetched [{self._exchange_manager.exchange_name}] full portfolio: "
            f"{personal_data.get_balance_summary(self.fetched_dependencies.fetched_exchange_data.authenticated_data.portfolio.full_content, use_exchange_format=False)}"
        )
        self._update_exchange_account_portfolio()

    def _update_exchange_account_portfolio(self):
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
            for asset, values in self.fetched_dependencies.fetched_exchange_data.authenticated_data.portfolio.full_content.items()
        ]

    def _get_traded_symbols(self) -> list[str]:
        profile_data = self.profile_data_provider.get_profile_data()
        config_symbols = scripting_library.get_traded_symbols(profile_data)
        return list_util.deduplicate(
            config_symbols + self.get_all_actions_symbols()
        )

    def get_all_actions_symbols(self) -> list[str]:
        return octobot_flow.logic.dsl.get_actions_symbol_dependencies(self.actions)

    def _get_time_frames(self) -> list[str]:
        return scripting_library.get_time_frames(self.profile_data_provider.get_profile_data())

    def _ensure_exchange_dependencies(self):
        if not self.fetched_dependencies.fetched_exchange_data:
            self.fetched_dependencies.fetched_exchange_data = octobot_flow.entities.FetchedExchangeData()

