from octobot_copy.copiers.futures_account_copier import FuturesAccountCopier
import octobot_copy.rebalancing.rebalancer.option_rebalancer as option_rebalancer


class OptionAccountCopier(FuturesAccountCopier):
    def get_rebalancer_class(self) -> type[option_rebalancer.OptionRebalancer]:
        return option_rebalancer.OptionRebalancer
