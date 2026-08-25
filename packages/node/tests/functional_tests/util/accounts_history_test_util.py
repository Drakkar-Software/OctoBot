#  Drakkar-Software OctoBot-Node

import contextlib
import datetime
import math

import mock

import octobot.community.authentication as community_authentication
import octobot_flow.logic.portfolio_history.portfolio_value_history as portfolio_value_history_module
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.api as trading_api


TEST_USER_ID = "0xaccountshistorytestwallet"
_TEST_PRIVATE_KEY = "accounts-history-test-private-key"
_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)

DAY_1_TS = 1700000000.0
DAY_2_TS = DAY_1_TS + 86400
BUY_TIME = datetime.datetime.fromtimestamp(DAY_1_TS + 3600, tz=datetime.timezone.utc)
DEPOSIT_TIME = datetime.datetime.fromtimestamp(DAY_2_TS + 1800, tz=datetime.timezone.utc)


def utc_day_start(timestamp: float) -> int:
    return int(math.floor(timestamp / 86400.0) * 86400)


def make_account(
    account_id: str,
    assets: dict[str, float],
    exchange: str = "binance",
    sandboxed: bool = False,
    is_simulated: bool = False,
) -> protocol_models.Account:
    detailed_assets = [
        protocol_models.DetailedAsset(symbol=symbol, total=amount, available=amount)
        for symbol, amount in assets.items()
    ]
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id="remote1",
        exchange_config_ids=["cfg1"],
    )
    return protocol_models.Account(
        id=account_id,
        name="Test",
        is_simulated=is_simulated,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        assets=[
            protocol_models.DetailedAssetsForTradingType(
                trading_type=protocol_models.TradingType.SPOT,
                assets=detailed_assets,
            )
        ],
    )


def make_exchange_config(
    exchange: str = "binance",
    sandboxed: bool = False,
) -> protocol_models.ExchangeConfig:
    return protocol_models.ExchangeConfig(
        id="cfg1",
        name="test",
        exchange=exchange,
        sandboxed=sandboxed,
        historical_trade_symbols=["BTC/USDT"],
    )


def make_protocol_trade(
    trade_id: str,
    symbol: str,
    side: protocol_models.Side,
    quantity: float,
    price: float,
    executed_at: datetime.datetime,
) -> protocol_models.Trade:
    return protocol_models.Trade(
        id=trade_id,
        trade_id=trade_id,
        type=protocol_models.OrderType.LIMIT,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        status=protocol_models.OrderStatus.FILLED,
        executed_at=executed_at,
    )


def make_protocol_transaction(
    tx_id: str,
    asset: str,
    amount: float,
    tx_type: protocol_models.TransactionType,
    timestamp: datetime.datetime,
) -> protocol_models.Transaction:
    return protocol_models.Transaction(
        id=tx_id,
        timestamp=timestamp,
        asset=asset,
        amount=amount,
        type=tx_type,
    )


def _patch_wallet(private_key: str = _TEST_PRIVATE_KEY):
    wallet = mock.Mock()
    wallet.private_key = private_key
    auth = mock.Mock()
    auth.get_wallet_by_user_id.return_value = wallet
    return mock.patch.object(
        community_authentication.CommunityAuthentication,
        "instance",
        return_value=auth,
    )


def seed_exchange_config(
    account_provider: collection_providers.AccountProvider,
    user_id: str,
    exchange_config: protocol_models.ExchangeConfig,
) -> None:
    account_provider.create_exchange_config(user_id, exchange_config)


def seed_account(
    account_provider: collection_providers.AccountProvider,
    user_id: str,
    account: protocol_models.Account,
) -> None:
    account_provider.create_account(user_id, account)


def seed_trading_state(
    trading_provider: collection_providers.AccountTradingProvider,
    user_id: str,
    account_id: str,
    *,
    trades: list[protocol_models.Trade] | None = None,
    transactions: list[protocol_models.Transaction] | None = None,
) -> None:
    trading_state = protocol_models.AccountTradingState(
        version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
        account_trading=protocol_models.AccountTrading(
            updated_at=_TEST_TIMESTAMP,
            trades=trades or None,
            transactions=transactions or None,
        ),
    )
    trading_provider.save_state(user_id, account_id, trading_state)


async def write_daily_prices_cache(
    data_root: str,
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    prices_by_symbol: dict[str, dict[str, float]],
) -> None:
    for symbol, closes_by_timestamp in prices_by_symbol.items():
        await trading_api.merge_daily_prices(
            exchange_name,
            exchange_type,
            sandboxed,
            symbol,
            closes_by_timestamp,
            data_root,
        )


async def write_latest_tickers_cache(
    data_root: str,
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
    closes_by_symbol: dict[str, float],
) -> None:
    await trading_api.update_latest_tickers(
        exchange_name,
        exchange_type,
        sandboxed,
        closes_by_symbol,
        data_root,
    )


@contextlib.contextmanager
def with_current_time(end_timestamp: float):
    with mock.patch.object(
        portfolio_value_history_module.time,
        "time",
        return_value=end_timestamp,
    ):
        yield


@contextlib.contextmanager
def accounts_history_test_environment(tmp_path):
    account_provider = collection_providers.AccountProvider(base_folder=str(tmp_path))
    trading_provider = collection_providers.AccountTradingProvider(base_folder=str(tmp_path))

    with (
        _patch_wallet(),
        mock.patch.object(
            collection_providers.AccountProvider,
            "instance",
            return_value=account_provider,
        ),
        mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ),
    ):
        yield account_provider, trading_provider
