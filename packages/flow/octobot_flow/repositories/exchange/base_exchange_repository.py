import octobot_trading.exchanges
import octobot_flow.entities
import octobot_trading.exchange_channel as exchange_channel
import octobot_trading.api

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

    def get_channel_updater(self, channel_name: str) -> exchange_channel.ExchangeChannelProducer:
        return octobot_trading.api.get_channel_updater(self.exchange_manager, channel_name)
