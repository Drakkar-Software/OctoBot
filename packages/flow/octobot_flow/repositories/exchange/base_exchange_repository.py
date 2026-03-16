import octobot_trading.exchanges
import octobot_flow.entities

class BaseExchangeRepository:
    def __init__(
        self,
        exchange_manager: octobot_trading.exchanges.ExchangeManager,
        known_automations: list[octobot_flow.entities.AutomationDetails],
        fetched_exchange_data: octobot_flow.entities.FetchedExchangeData,
    ):
        self.exchange_manager: octobot_trading.exchanges.ExchangeManager = exchange_manager
        self.known_automations: list[octobot_flow.entities.AutomationDetails] = known_automations
        self.fetched_exchange_data: octobot_flow.entities.FetchedExchangeData = fetched_exchange_data
