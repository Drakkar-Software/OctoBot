import dataclasses
import octobot_commons.dataclasses
import octobot_copy.entities


@dataclasses.dataclass
class TradingSignal(octobot_commons.dataclasses.MinimizableDataclass):
    strategy_id: str
    account: octobot_copy.entities.Account
