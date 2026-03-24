import octobot_copy.copiers.spot_account_copier
import octobot_copy.rebalancing.rebalancer.futures_rebalancer as futures_rebalancer


class FuturesAccountCopier(octobot_copy.copiers.spot_account_copier.SpotAccountCopier):
    def get_rebalancer_class(self) -> type[futures_rebalancer.FuturesRebalancer]:
        return futures_rebalancer.FuturesRebalancer
