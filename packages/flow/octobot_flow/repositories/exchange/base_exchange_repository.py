import typing

import octobot_trading.exchanges
import octobot_flow.entities
import octobot_trading.exchange_channel as exchange_channel

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
        for name, channel in exchange_channel.get_exchange_channels(self.exchange_manager.id).items():
            if name == channel_name:
                if producers := channel.get_producers():
                    updater = producers[0]
                    if isinstance(updater, exchange_channel.ExchangeChannelProducer):
                        return updater
                raise KeyError(
                    f"Missing producer for channel {channel_name}"
                )
        raise KeyError(
            f"Channel {channel_name} not found for exchange {self.exchange_manager.exchange_name}"
        )
