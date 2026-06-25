#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
import dataclasses

import octobot_commons.dataclasses

import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import


@dataclasses.dataclass
class Metadata(octobot_commons.dataclasses.MinimizableDataclass):
    """
    Timestamps and child PID written with process bot state dumps. Liveness checks use
    updated_at / next_updated_at only; pid is the authoritative child PID for parent binding
    after restarts.
    """

    updated_at: float = 0.0
    next_updated_at: float = 0.0
    pid: int = 0


@dataclasses.dataclass
class ProcessBotState(octobot_commons.dataclasses.MinimizableDataclass):
    """
    Serialized JSON next to the user config when --dump-state is enabled. Liveness is driven by
    metadata.updated_at / metadata.next_updated_at only. exchange_account_elements is a single
    snapshot for the dumped trading exchange (see process_bot_state_dumper).
    """

    metadata: Metadata = dataclasses.field(default_factory=Metadata)
    exchange_account_elements: exchange_account_elements_import.ExchangeAccountElements = (
        dataclasses.field(default_factory=exchange_account_elements_import.ExchangeAccountElements)
    )

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            self.metadata = Metadata.from_dict(self.metadata)
        if isinstance(self.exchange_account_elements, dict):
            self.exchange_account_elements = (
                exchange_account_elements_import.ExchangeAccountElements.from_dict(
                    self.exchange_account_elements
                )
            )
