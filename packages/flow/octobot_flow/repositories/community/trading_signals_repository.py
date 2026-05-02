import starfish_sdk
import dataclasses

import octobot_commons.dataclasses
import octobot_flow.entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.community_repository as community_repository
import octobot_commons.logging as logging


VERSION = "1.0.0"


@dataclasses.dataclass
class TradingSignalPayload(octobot_commons.dataclasses.MinimizableDataclass):
    signals: list[octobot_flow.entities.TradingSignal] = dataclasses.field(default_factory=list, repr=True)

    def __post_init__(self):
        if self.signals and isinstance(self.signals[0], dict):
            self.signals = [
                octobot_flow.entities.TradingSignal.from_dict(signal)
                for signal in self.signals
            ]


def _sync_signals_path(sync_kind: str, strategy_id: str) -> str:
    return f"/v1/{sync_kind}/products/{strategy_id}/signals/{VERSION}"


def _trim_historical_snapshots_if_needed(
    trading_signal: octobot_flow.entities.TradingSignal,
    history_size: int,
) -> None:
    account = trading_signal.account
    if not account.historical_snapshots or len(account.historical_snapshots) <= history_size:
        return
    account.historical_snapshots = account.historical_snapshots[:history_size]


class TradingSignalsRepository(community_repository.CommunityRepository):
    async def insert_trading_signal(self, trading_signal: octobot_flow.entities.TradingSignal):
        await trading_signals_channel.send_internal_trading_signal(trading_signal)
        await self._upload_trading_signal(trading_signal)

    async def fetch_trading_signals(
        self,
        strategy_ids: list[str],
        history_size: int,
    ) -> list[octobot_flow.entities.TradingSignal]:
        trading_signals: list[octobot_flow.entities.TradingSignal] = []
        for strategy_identifier in strategy_ids:
            try:
                manager = self._get_sync_manager(strategy_identifier)
                trading_signal = (await self._pull_trading_signals(manager)).signals
                _trim_historical_snapshots_if_needed(trading_signal, history_size)
                trading_signals.append(trading_signal)
            except Exception as strategy_error:
                self._logger().exception(
                    strategy_error,
                    True,
                    f"Failed to fetch trading signals for strategy {strategy_identifier!r}: {strategy_error}",
                )
        return trading_signals

    async def _upload_trading_signal(
        self,
        trading_signal: octobot_flow.entities.TradingSignal,
    ):
        manager = self._get_sync_manager(trading_signal.strategy_id)
        previous_signals = await self._pull_trading_signals(manager)
        payload = TradingSignalPayload(signals=previous_signals.signals + [trading_signal])
        try:
            await manager.push(payload.to_dict())
        except Exception as upload_error:
            self._logger().exception(upload_error, True, f"Failed to upload trading signal: {upload_error}")

    async def _pull_trading_signals(
        self, manager: starfish_sdk.SyncManager
    ) -> TradingSignalPayload:
        return TradingSignalPayload.from_dict((await manager.pull()).data)

    def _get_sync_manager(self, strategy_id: str) -> starfish_sdk.SyncManager:
        return starfish_sdk.SyncManager(
            client=self._get_sync_client(),
            pull_path=_sync_signals_path("pull", strategy_id),
            push_path=_sync_signals_path("push", strategy_id),
            sign_data=self.authenticator._sync_data_signer,
        )

    def _logger(self) -> logging.BotLogger:
        return logging.get_logger("TradingSignalsRepository")
