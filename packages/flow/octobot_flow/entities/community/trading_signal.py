import dataclasses

import octobot_commons.dataclasses
import octobot_protocol.models as protocol_models


@dataclasses.dataclass
class TradingSignal(octobot_commons.dataclasses.MinimizableDataclass):
    strategy_id: str = dataclasses.field(repr=True)
    account: protocol_models.CopiedAccount = dataclasses.field(repr=True)
