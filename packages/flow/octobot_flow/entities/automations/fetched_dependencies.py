import dataclasses
import typing

import octobot_commons.dataclasses

import octobot_flow.entities.automations.fetched_exchange_data as fetched_exchange_data_import
import octobot_flow.entities.automations.fetched_copy_trading_data as fetched_copy_trading_data_import

@dataclasses.dataclass
class FetchedDependencies(octobot_commons.dataclasses.MinimizableDataclass):
    fetched_exchange_data: typing.Optional[fetched_exchange_data_import.FetchedExchangeData] = None
    fetched_copy_trading_data: typing.Optional[fetched_copy_trading_data_import.FetchedCopyTradingData] = None
