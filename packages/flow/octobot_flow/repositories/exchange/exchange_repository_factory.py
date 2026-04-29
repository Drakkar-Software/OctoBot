import octobot_trading.exchanges

import octobot_flow.entities
import octobot_flow.repositories.exchange.simulated_trading as simulated_trading_repositories
import octobot_flow.repositories.exchange.ohlcv_repository as ohlcv_repository_import
import octobot_flow.repositories.exchange.orders_repository as orders_repository_import
import octobot_flow.repositories.exchange.portfolio_repository as portfolio_repository_import
import octobot_flow.repositories.exchange.positions_repository as positions_repository_import
import octobot_flow.repositories.exchange.trades_repository as trades_repository_import
import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_import



class ExchangeRepositoryFactory:
    def __init__(
        self,
        exchange_manager: octobot_trading.exchanges.ExchangeManager,
        known_automations: list[octobot_flow.entities.AutomationDetails],
        fetched_exchange_data: octobot_flow.entities.FetchedExchangeData,
        is_simulated: bool,
    ):
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = exchange_manager
        self.known_automations: list[octobot_flow.entities.AutomationDetails] = known_automations
        self.fetched_exchange_data: octobot_flow.entities.FetchedExchangeData = fetched_exchange_data
        self.is_simulated: bool = is_simulated

    def get_ohlcv_repository(self) -> ohlcv_repository_import.OhlcvRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedOhlcvRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return ohlcv_repository_import.OhlcvRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )

    def get_orders_repository(self) -> orders_repository_import.OrdersRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedOrdersRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return orders_repository_import.OrdersRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )

    def get_portfolio_repository(self) -> portfolio_repository_import.PortfolioRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedPortfolioRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return portfolio_repository_import.PortfolioRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )

    def get_positions_repository(self) -> positions_repository_import.PositionsRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedPositionsRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return positions_repository_import.PositionsRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )

    def get_trades_repository(self) -> trades_repository_import.TradesRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedTradesRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return trades_repository_import.TradesRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )

    def get_tickers_repository(self) -> tickers_repository_import.TickersRepository:
        if self.is_simulated:
            return simulated_trading_repositories.SimulatedTickersRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
        else:
            return tickers_repository_import.TickersRepository(
                self.exchange_manager, self.known_automations, self.fetched_exchange_data
            )
