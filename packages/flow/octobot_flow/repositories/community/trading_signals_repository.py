import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_commons.json_util
import octobot_commons.constants
import octobot_commons.logging as logging
import octobot_sync.client
import octobot_flow.entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.community_repository as community_repository
import octobot_flow.errors
import octobot_flow.constants


VERSION = "1.0.0"


def _trading_signal_fingerprint(signal: octobot_flow.entities.TradingSignal) -> tuple[str, float]:
    """Stable identity for dedupe across JSON round-trips (float normalizes Decimal)."""
    return (signal.strategy_id, float(signal.account.updated_at))


def _signals_sorted_chronologically(
    signals: list[octobot_flow.entities.TradingSignal],
) -> list[octobot_flow.entities.TradingSignal]:
    """Sort by ``account.updated_at``, then original index when timestamps tie."""
    indexed = list(enumerate(signals))
    indexed.sort(key=lambda index_signal: (float(index_signal[1].account.updated_at), index_signal[0]))
    return [signal for _, signal in indexed]


@dataclasses.dataclass
class TradingSignalPayload(octobot_commons.dataclasses.MinimizableDataclass):
    signals: list[octobot_flow.entities.TradingSignal] = dataclasses.field(default_factory=list, repr=True)

    def __post_init__(self):
        if self.signals and isinstance(self.signals[0], dict):
            self.signals = [
                octobot_flow.entities.TradingSignal.from_dict(signal)
                for signal in self.signals
            ]

    def merge_with_remote(self, remote: "TradingSignalPayload") -> "TradingSignalPayload":
        """Combine server history with client-only snapshots for optimistic-concurrency merge."""
        remote_ordered = _signals_sorted_chronologically(remote.signals)
        remote_fingerprints = {_trading_signal_fingerprint(signal) for signal in remote_ordered}
        local_ordered = _signals_sorted_chronologically(self.signals)
        local_only = [
            signal
            for signal in local_ordered
            if _trading_signal_fingerprint(signal) not in remote_fingerprints
        ]
        return TradingSignalPayload(signals=remote_ordered + local_only)


def _sync_signals_path(sync_kind: str, strategy_id: str) -> str:
    return f"/v1/{sync_kind}/products/{strategy_id}/{VERSION}/signals"


def _merge_trading_signal_documents(
    local_payload: dict[str, typing.Any],
    remote_payload: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    """Merge pending client document with server state after a sync push conflict (409)."""
    local_model = TradingSignalPayload.from_dict(local_payload if isinstance(local_payload, dict) else {})
    remote_model = TradingSignalPayload.from_dict(remote_payload if isinstance(remote_payload, dict) else {})
    return octobot_commons.json_util.sanitize(
        local_model.merge_with_remote(remote_model).to_dict()
    )


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
                pulled_signals = await self._pull_trading_signals(
                    self._get_sync_client(), strategy_identifier, history_size
                )
                if not pulled_signals.signals:
                    continue
                trading_signal = max(
                    pulled_signals.signals,
                    key=lambda signal: signal.account.updated_at,
                )
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
        client = self._get_sync_client()
        payload = octobot_commons.json_util.sanitize(trading_signal.to_dict())
        try:
            await octobot_sync.client.append_payload(
                client,
                push_path=_sync_signals_path("push", trading_signal.strategy_id),
                payload=payload,
                timestamp=int(trading_signal.account.updated_at * octobot_commons.constants.MSECONDS_TO_SECONDS),
            )
        except Exception as upload_error:
            self._logger().exception(upload_error, True, f"Failed to upload trading signal: {upload_error}")

    async def _pull_trading_signals(
        self, client: octobot_sync.client.StarfishClient, strategy_id: str, last: typing.Optional[int]
    ) -> TradingSignalPayload:
        signals = await client.pull(
            _sync_signals_path("pull", strategy_id),
            last=last
        )
        if not isinstance(signals, list):
            raise octobot_flow.errors.CommunityTradingSignalError(f"Unexpected response type: {type(signals)}")
        return TradingSignalPayload(
            signals=[
                octobot_flow.entities.TradingSignal.from_dict(signal["data"]) for signal in signals
            ]
        )

    def _logger(self) -> logging.BotLogger:
        return logging.get_logger("TradingSignalsRepository")
