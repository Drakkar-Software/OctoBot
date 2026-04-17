import dataclasses
import octobot_commons.dataclasses
import octobot_copy.entities


@dataclasses.dataclass
class TradingSignal(octobot_commons.dataclasses.MinimizableDataclass):
    strategy_id: str = dataclasses.field(repr=True)
    account: octobot_copy.entities.Account = dataclasses.field(repr=True)
