from octobot_copy.copiers.account_copier import AccountCopier
import octobot_copy.rebalancing.rebalancer.spot_rebalancer as spot_rebalancer


class SpotAccountCopier(AccountCopier):
    """Spot account copy: executes rebalance via SpotRebalancer (no contract prep per coin)."""

    def get_rebalancer_class(self) -> type[spot_rebalancer.SpotRebalancer]:
        return spot_rebalancer.SpotRebalancer
