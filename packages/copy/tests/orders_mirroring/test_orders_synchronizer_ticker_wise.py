import decimal
import mock
import time

import octobot_protocol.models as protocol_models
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities
import octobot_copy.orders_mirroring.orders_synchronizer as orders_synchronizer_import

TICKER_WISE_SYMBOL = "BTC@BTC/USDT@ETH"


class TestScaleMirroredOrderQuantityTickerWise:
    def test_buy_scales_using_quote_portfolio_asset(self):
        synchronizer = orders_synchronizer_import.OrdersSynchronizer.__new__(
            orders_synchronizer_import.OrdersSynchronizer
        )
        synchronizer._reference_account = mock.Mock()
        synchronizer._exchange_interface = mock.Mock()
        synchronizer._exchange_interface.portfolio.get_currency_portfolio_total = mock.Mock(
            return_value=decimal.Decimal("200")
        )
        with mock.patch(
            "octobot_copy.orders_mirroring.orders_synchronizer.copy_entities.copied_asset_total_by_name",
            mock.Mock(return_value={"USDT@ETH": decimal.Decimal("100")}),
        ):
            order = mock.Mock(quantity="10")
            scaled = synchronizer._scale_mirrored_order_quantity(
                order, TICKER_WISE_SYMBOL, trading_enums.TradeOrderSide.BUY
            )
        assert scaled == decimal.Decimal("20")


class TestReferencePairLegShareNetworkQualified:
    def test_uses_portfolio_asset_ratio_keys(self):
        reference = protocol_models.CopiedAccount(
            version=copy_constants.COPIED_ACCOUNT_VERSION,
            updated_at=time.time(),
            copied_assets=[
                protocol_models.CopiedAsset(
                    name="BTC@BTC", total=1.0, available=1.0, ratio=0.25
                ),
                protocol_models.CopiedAsset(
                    name="USDT@ETH", total=1.0, available=1.0, ratio=0.5
                ),
            ],
            orders=[],
        )
        synchronizer = orders_synchronizer_import.OrdersSynchronizer(
            reference,
            mock.MagicMock(),
            copy_entities.AccountCopySettings(),
        )
        expected = decimal.Decimal("0.25") / (
            decimal.Decimal("0.25") + decimal.Decimal("0.5")
        )
        assert synchronizer._reference_pair_leg_share(TICKER_WISE_SYMBOL) == expected
