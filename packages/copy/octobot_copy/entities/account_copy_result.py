import dataclasses
import typing

import octobot_commons.dataclasses as commons_dataclasses


@dataclasses.dataclass
class AccountCopyResult(commons_dataclasses.MinimizableDataclass):
    """Outcome of AccountCopier.copy_account (rebalance + mirrored order sync)."""

    # Placed copier orders (octobot_trading.personal_data.Order instances)
    created_orders: list = dataclasses.field(default_factory=list)
    # Wall time.time() when mirrored-orphan grace episode started, if any; None when idle
    open_orders_grace_period_started_at: typing.Optional[float] = None
