import dataclasses
import octobot_commons.dataclasses
import octobot_flow.entities.community.trading_signal as trading_signal_import


@dataclasses.dataclass
class FetchedCopyTradingData(octobot_commons.dataclasses.MinimizableDataclass):
    trading_signals: list[trading_signal_import.TradingSignal] = dataclasses.field(default_factory=list, repr=True)

    def __post_init__(self):
        if self.trading_signals and isinstance(self.trading_signals[0], dict):
            self.trading_signals = [
                trading_signal_import.TradingSignal.from_dict(trading_signal)
                for trading_signal in self.trading_signals
            ]

    def __bool__(self) -> bool:
        return bool(self.trading_signals)
