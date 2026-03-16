import dataclasses
import octobot_commons.dataclasses


@dataclasses.dataclass
class AdditionalActions(octobot_commons.dataclasses.FlexibleDataclass):
    # todo implement this when necessary
    check_min_portfolio: bool = False
    optimize_portfolio: bool = False
    optimize_portfolio_for_restart: bool = False
    trigger_initial_orders: bool = False
    minimum_wait_time_before_next_iteration: float = 0

    @classmethod
    def default_iteration(cls):
        return cls(
            check_min_portfolio=False, optimize_portfolio=False,
            optimize_portfolio_for_restart=False, trigger_initial_orders=False
        )

    def has_trading_actions(self) -> bool:
        return self.optimize_portfolio or self.optimize_portfolio_for_restart
