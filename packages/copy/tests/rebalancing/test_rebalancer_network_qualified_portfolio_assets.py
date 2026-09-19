import decimal

import mock
import pytest

import octobot_copy.enums as copy_enums
import octobot_trading.enums as trading_enums
import octobot_trading.errors as trading_errors
import octobot_copy.rebalancing.rebalancer.spot_rebalancer as spot_rebalancer

TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


def _remove_only_details(remove_asset: str) -> dict:
    return {
        copy_enums.RebalanceDetails.REMOVE.value: {remove_asset: decimal.Decimal("1")},
        copy_enums.RebalanceDetails.BUY_MORE.value: {},
        copy_enums.RebalanceDetails.ADD.value: {},
        copy_enums.RebalanceDetails.SWAP.value: {},
    }


class TestRebalancerSoldCoinsNetworkQualified:
    @pytest.mark.asyncio
    async def test_removed_asset_matches_sell_order_portfolio_base(self):
        rebalancer = spot_rebalancer.SpotRebalancer(mock.Mock(), mock.Mock(), {})
        details = _remove_only_details("BTC@BTC")
        removed_orders = [
            mock.Mock(symbol=TICKER_WISE_SYMBOL, side=trading_enums.TradeOrderSide.SELL)
        ]
        await rebalancer._validate_sold_removed_assets(details, removed_orders)

    @pytest.mark.asyncio
    async def test_removed_asset_mismatch_raises(self):
        rebalancer = spot_rebalancer.SpotRebalancer(mock.Mock(), mock.Mock(), {})
        rebalancer._get_logger = mock.Mock(return_value=mock.Mock())
        details = _remove_only_details("BTC@BTC")
        removed_orders = [
            mock.Mock(symbol=TICKER_WISE_SYMBOL, side=trading_enums.TradeOrderSide.BUY)
        ]
        with pytest.raises(trading_errors.MissingMinimalExchangeTradeVolume):
            await rebalancer._validate_sold_removed_assets(details, removed_orders)
