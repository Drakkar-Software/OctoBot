import octobot.community

import octobot_flow.entities


class TradingSignalsRepository:
    def __init__(self, authenticator: octobot.community.CommunityAuthentication):
        self.authenticator: octobot.community.CommunityAuthentication = authenticator

    async def insert_trading_signal(self, trading_signal: octobot_flow.entities.TradingSignal):
        raise NotImplementedError("TODO: insert_trading_signal")

    async def fetch_trading_signals(self, user_id: str) -> list[octobot_flow.entities.TradingSignal]:
        raise NotImplementedError("TODO: fetch_trading_signals")
