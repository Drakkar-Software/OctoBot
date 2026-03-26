import octobot_trading.personal_data as trading_personal_data

import octobot_copy.copiers.spot_account_copier as spot_account_copier
import octobot_copy.rebalancing.rebalancer.futures_rebalancer as futures_rebalancer


class FuturesAccountCopier(spot_account_copier.SpotAccountCopier):
    def get_rebalancer_class(self) -> type[futures_rebalancer.FuturesRebalancer]:
        return futures_rebalancer.FuturesRebalancer

    async def _synchronize_reference_open_orders(self) -> list[trading_personal_data.Order]:
        raise NotImplementedError(
            "Reference open-order replication on futures is not implemented yet."
        )
