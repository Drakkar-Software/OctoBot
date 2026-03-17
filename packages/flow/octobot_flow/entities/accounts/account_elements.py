import dataclasses
import typing

import octobot_commons.dataclasses
import octobot_trading.exchanges.util.exchange_data as exchange_data_import



@dataclasses.dataclass
class AccountElements(octobot_commons.dataclasses.MinimizableDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    """
    Defines the ideal exchange account state of an automation. Only contains sharable data
    """
    name: typing.Optional[str] = None
    portfolio: exchange_data_import.PortfolioDetails = dataclasses.field(default_factory=exchange_data_import.PortfolioDetails)
    transactions: list[dict] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.portfolio and isinstance(self.portfolio, dict):
            self.portfolio = exchange_data_import.PortfolioDetails.from_dict(self.portfolio)
