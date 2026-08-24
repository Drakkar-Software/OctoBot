import dataclasses
import typing

import starfish_spaces

import octobot_commons.dataclasses
import octobot_commons.json_util
import octobot_commons.constants
import octobot_commons.logging as logging
import octobot_sync.artifacts
import octobot_flow.entities
import octobot_flow.errors
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.community_repository as community_repository
import octobot_flow.constants


# artifact-events "version" path segment: a fixed wire-schema version, not a strategy revision.
VERSION = "1.0.0"


def _signal_space_id(strategy_id: str) -> str:
    return octobot_sync.artifacts.artifact_space_id(f"octobot-signals-{strategy_id}")


@dataclasses.dataclass
class TradingSignalPayload(octobot_commons.dataclasses.MinimizableDataclass):
    signals: list[octobot_flow.entities.TradingSignal] = dataclasses.field(default_factory=list, repr=True)

    def __post_init__(self):
        if self.signals and isinstance(self.signals[0], dict):
            self.signals = [
                octobot_flow.entities.TradingSignal.from_dict(signal)
                for signal in self.signals
            ]


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
        session: typing.Optional[starfish_spaces.Session] = None
        failed_strategy_ids: list[str] = []
        first_failure: typing.Optional[Exception] = None
        for strategy_identifier in strategy_ids:
            try:
                if session is None:
                    session = await self._get_signal_session()
                pulled_signals = await self._pull_trading_signals(
                    session, strategy_identifier, history_size
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
                failed_strategy_ids.append(strategy_identifier)
                if first_failure is None:
                    first_failure = strategy_error
        if failed_strategy_ids:
            raise octobot_flow.errors.CommunityTradingSignalError(
                f"Failed to fetch trading signals for {', '.join(failed_strategy_ids)}: {first_failure}"
            ) from first_failure
        return trading_signals

    async def _upload_trading_signal(
        self,
        trading_signal: octobot_flow.entities.TradingSignal,
    ):
        payload = octobot_commons.json_util.sanitize(trading_signal.to_dict())
        try:
            session = await self._get_signal_session()
            await octobot_sync.artifacts.publish_artifact_event(
                session,
                _signal_space_id(trading_signal.strategy_id),
                VERSION,
                payload,
                ts=int(trading_signal.account.updated_at * octobot_commons.constants.MSECONDS_TO_SECONDS),
            )
        except Exception as upload_error:
            self._logger().exception(upload_error, True, f"Failed to upload trading signal: {upload_error}")

    async def _pull_trading_signals(
        self,
        session: starfish_spaces.Session,
        strategy_id: str,
        last: typing.Optional[int],
        *,
        owner_ed_pub: typing.Optional[str] = None,
    ) -> TradingSignalPayload:
        signals = await octobot_sync.artifacts.pull_artifact_events(
            session, _signal_space_id(strategy_id), VERSION, last, owner_ed_pub=owner_ed_pub
        )
        return TradingSignalPayload(
            signals=[
                octobot_flow.entities.TradingSignal.from_dict(signal) for signal in signals
            ]
        )

    def _logger(self) -> logging.BotLogger:
        return logging.get_logger("TradingSignalsRepository")
