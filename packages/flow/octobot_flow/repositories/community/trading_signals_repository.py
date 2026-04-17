import octobot.community

import octobot_flow.entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel


class TradingSignalsRepository:
    def __init__(self, authenticator: octobot.community.CommunityAuthentication):
        self.authenticator: octobot.community.CommunityAuthentication = authenticator

    async def insert_trading_signal(self, trading_signal: octobot_flow.entities.TradingSignal):
        await trading_signals_channel.send_internal_trading_signal(trading_signal)

    async def fetch_trading_signals(self, strategy_ids: list[str], history_size: int) -> list[octobot_flow.entities.TradingSignal]:
        raise NotImplementedError("TODO: fetch_trading_signals")
