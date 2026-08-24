import datetime
import decimal
import json
import os
import mock
import pytest

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants

import octobot_node.protocol.accounts_history as accounts_history_module


def _make_account(
    account_id: str,
    assets: dict[str, float],
    exchange: str = "binance",
    sandboxed: bool = False,
) -> protocol_models.Account:
    detailed_assets = [
        protocol_models.DetailedAsset(symbol=symbol, total=amount, available=amount)
        for symbol, amount in assets.items()
    ]
    exchange_config = protocol_models.ExchangeConfig(
        id="cfg1", name="test", exchange=exchange, sandboxed=sandboxed,
        historical_trade_symbols=["BTC/USDT"],
    )
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote1",
        exchange_config_ids=["cfg1"],
    )
    return protocol_models.Account(
        id=account_id,
        name="Test",
        is_simulated=False,
        created_at=datetime.datetime.now(datetime.timezone.utc),
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=detailed_assets,
            )
        ],
    )


class TestPortfolioFromAccountAssets:
    def test_converts_assets_to_portfolio_dict(self):
        account = _make_account("a1", {"BTC": 1.5, "USDT": 10000.0})
        portfolio = accounts_history_module._portfolio_from_account_assets(account)
        assert portfolio["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("1.5")
        assert portfolio["USDT"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("10000.0")

    def test_empty_assets(self):
        account = mock.MagicMock(spec=protocol_models.Account)
        account.assets = None
        portfolio = accounts_history_module._portfolio_from_account_assets(account)
        assert portfolio == {}


class TestComputePortfolioHistoricalValues:
    @pytest.mark.asyncio
    @mock.patch("octobot_sync.sync.collection_providers.AccountProvider")
    @mock.patch("octobot_sync.sync.collection_providers.AccountTradingProvider")
    async def test_empty_trading_returns_empty_history(self, mock_trading_provider, mock_account_provider, tmp_path):
        account = _make_account("a1", {"BTC": 1.0})
        mock_account_provider.instance.return_value.get_account.return_value = account
        mock_account_provider.instance.return_value.get_exchange_config.return_value = protocol_models.ExchangeConfig(
            id="cfg1", name="test", exchange="binance", sandboxed=False,
            historical_trade_symbols=["BTC/USDT"],
        )

        trading_state = mock.MagicMock()
        trading_state.account_trading.trades = []
        trading_state.account_trading.transactions = []
        mock_trading_provider.instance.return_value.load_state.return_value = trading_state

        result = await accounts_history_module.compute_portfolio_historical_values_from_latest_portfolio_trades_and_transactions(
            "user1", "a1",
        )
        assert result.version == sync_constants.USER_ACCOUNTS_HISTORY_STATE_VERSION
        # No trades/transactions → no history values.
        if result.history is not None:
            assert result.history.values is None or len(result.history.values) == 0
