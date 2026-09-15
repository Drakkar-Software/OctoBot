#  Drakkar-Software OctoBot-Flow

import contextlib
import datetime

import mock

import octobot.community.authentication as community_authentication
import octobot_commons.tests.test_config as test_config_module
import octobot_protocol.models as protocol_models
import octobot_sync.constants as sync_constants
import octobot_sync.sync.collection_providers as collection_providers
import octobot_trading.api as trading_api
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.exchange_manager as exchange_manager_module
import octobot_trading.exchanges.traders.trader_simulator as trader_simulator_module
import octobot_trading.exchanges.util.exchange_data as exchange_data_module
import octobot_trading.personal_data.trades.protocol as trades_protocol

import octobot_flow.entities.portfolio_history as portfolio_history_entities
import octobot_flow.jobs.portfolio_history_job as portfolio_history_job_module
import octobot_flow.logic.portfolio_history.daily_price_cache_updater as daily_price_cache_updater_module
import tests.repositories.exchange.trades_repository_test_util as trades_repository_test_util


TEST_WALLET_ID = "0xfunctionaltestwallet"
_TEST_WALLET_ID = TEST_WALLET_ID
_TEST_PRIVATE_KEY = "functional-test-private-key"
_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)
_DEFAULT_SYMBOL = "BTC/USDT"
_DEFAULT_ACCOUNT_ASSET_SYMBOLS = ["BTC", "ETH", "USDT"]


def default_spot_account_assets(
    symbols: list[str] | None = None,
) -> list[protocol_models.DetailedAssetsForTradingType]:
    resolved_symbols = symbols or _DEFAULT_ACCOUNT_ASSET_SYMBOLS
    return [
        protocol_models.DetailedAssetsForTradingType(
            trading_type=protocol_models.TradingType.SPOT,
            assets=[
                protocol_models.DetailedAsset(
                    symbol=symbol,
                    total=1.0,
                    available=1.0,
                )
                for symbol in resolved_symbols
            ],
        )
    ]


def build_portfolio_history_context(
    *,
    account_id: str = "functional-account-1",
    symbols: list[str] | None = None,
    trade_symbols: list[str] | None = None,
    is_simulated: bool = False,
    exchange: str = "binanceus",
    assets: list[protocol_models.DetailedAssetsForTradingType] | None = None,
) -> portfolio_history_entities.PortfolioHistoryAccountContext:
    exchange_account = protocol_models.ExchangeAccount(
        account_type=protocol_models.AccountType.EXCHANGE,
        remote_account_id=account_id,
        exchange_config_ids=["exchange-config-1"],
    )
    account = protocol_models.Account(
        id=account_id,
        name="Functional portfolio history account",
        is_simulated=is_simulated,
        created_at=_TEST_TIMESTAMP,
        updated_at=_TEST_TIMESTAMP,
        specifics=protocol_models.AccountSpecifics(actual_instance=exchange_account),
        assets=default_spot_account_assets() if assets is None else assets,
    )
    exchange_config = protocol_models.ExchangeConfig(
        id="exchange-config-1",
        name="binance-main",
        exchange=exchange,
        sandboxed=False,
        historical_trade_symbols=symbols or [_DEFAULT_SYMBOL],
    )
    auth_details = exchange_data_module.ExchangeAuthDetails(
        exchange_type=trading_enums.ExchangeTypes.SPOT.value,
        sandboxed=False,
        exchange_account_id=account_id,
        api_key=account_id,
    )
    resolved_trade_symbols = (
        trade_symbols
        if trade_symbols is not None
        else (symbols or [_DEFAULT_SYMBOL])
    )
    return portfolio_history_entities.PortfolioHistoryAccountContext(
        account=account,
        exchange_account=exchange_account,
        exchange_config=exchange_config,
        trading_type=protocol_models.TradingType.SPOT,
        auth_details=auth_details,
        trade_symbols=list(resolved_trade_symbols),
    )


def sample_raw_trade(
    *,
    trade_id: str = "functional-trade-1",
    symbol: str = _DEFAULT_SYMBOL,
    timestamp: float = 1700000000.0,
) -> dict:
    return {
        "info": {},
        "id": trade_id,
        "exchange_id": trade_id,
        "exchange_trade_id": trade_id,
        "timestamp": timestamp,
        "symbol": symbol,
        "type": "limit",
        "side": "buy",
        "price": 30000.0,
        "amount": 0.1,
        "cost": 3000.0,
        "status": "closed",
        "fee": {"cost": 0.0, "currency": "USDT"},
    }


def sample_deposit(
    *,
    txid: str = "functional-deposit-1",
    currency: str = "BTC",
    amount: float = 1.0,
) -> dict:
    return {
        trading_enums.ExchangeConstantsTransactionColumns.TXID.value: txid,
        trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency,
        trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount,
        trading_enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: 1700001000,
        trading_enums.ExchangeConstantsTransactionColumns.TYPE.value: (
            trading_enums.TransactionType.BLOCKCHAIN_DEPOSIT.value
        ),
    }


def sample_withdrawal(
    *,
    txid: str = "functional-withdrawal-1",
    currency: str = "ETH",
    amount: float = 0.5,
) -> dict:
    return {
        trading_enums.ExchangeConstantsTransactionColumns.TXID.value: txid,
        trading_enums.ExchangeConstantsTransactionColumns.CURRENCY.value: currency,
        trading_enums.ExchangeConstantsTransactionColumns.AMOUNT.value: amount,
        trading_enums.ExchangeConstantsTransactionColumns.TIMESTAMP.value: 1700002000,
        trading_enums.ExchangeConstantsTransactionColumns.TYPE.value: (
            trading_enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value
        ),
    }


def sample_daily_candles(
    *,
    day_timestamp: int = 86400,
    close_price: float = 40500.0,
) -> list[list[float]]:
    return [
        [day_timestamp, 40000.0, 41000.0, 39000.0, close_price, 100.0],
    ]


async def _create_exchange_manager_with_trader() -> exchange_manager_module.ExchangeManager:
    config = test_config_module.load_test_config()
    exchange_manager = exchange_manager_module.ExchangeManager(config, "binanceus")
    await exchange_manager.initialize(exchange_config_by_exchange=None)
    trader = trader_simulator_module.TraderSimulator(config, exchange_manager)
    await trader.initialize()
    return exchange_manager


async def build_exchange_manager(
    *,
    raw_trades: list[dict] | None = None,
    deposits: list[dict] | None = None,
    withdrawals: list[dict] | None = None,
    daily_candles: list[list[float]] | None = None,
    client_side_trade_filter: bool = False,
) -> exchange_manager_module.ExchangeManager:
    exchange_manager = await _create_exchange_manager_with_trader()

    configured_raw_trades = raw_trades if raw_trades is not None else []
    configured_deposits = deposits or []
    configured_withdrawals = withdrawals or []
    configured_daily_candles = daily_candles or sample_daily_candles()
    trade_fetch_calls: list[dict] = []

    async def get_my_recent_trades(symbol=None, limit=None, since=None, exhaust_history=False, **_kwargs):
        trade_fetch_calls.append(
            {
                "symbol": symbol,
                "limit": limit,
                "since": since,
                "exhaust_history": exhaust_history,
            }
        )
        matched_trades = list(configured_raw_trades)
        if symbol is not None:
            matched_trades = [
                raw_trade
                for raw_trade in matched_trades
                if raw_trade.get(trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value) == symbol
            ]
        if since is not None:
            matched_trades = [
                raw_trade
                for raw_trade in matched_trades
                if int(float(raw_trade.get(trading_enums.ExchangeConstantsOrderColumns.TIMESTAMP.value, 0)) * 1000)
                >= since
            ]
        if limit is not None:
            matched_trades = matched_trades[:limit]
        return matched_trades

    exchange_manager.trade_fetch_calls = trade_fetch_calls
    exchange_manager.exchange.get_my_recent_trades = get_my_recent_trades
    exchange_manager.exchange.get_option_value = mock.Mock(
        return_value=client_side_trade_filter,
    )
    exchange_manager.exchange.get_deposits = mock.AsyncMock(return_value=configured_deposits)
    exchange_manager.exchange.get_withdrawals = mock.AsyncMock(return_value=configured_withdrawals)
    exchange_manager.exchange.get_symbol_prices = mock.AsyncMock(return_value=configured_daily_candles)
    await trades_repository_test_util.ensure_trades_channel(exchange_manager)
    return exchange_manager


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


def seed_empty_account_trading(
    provider: collection_providers.AccountTradingProvider,
    wallet_id: str,
    account_id: str,
) -> None:
    trading_state = protocol_models.AccountTradingState(
        version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
        account_trading=protocol_models.AccountTrading(
            updated_at=_TEST_TIMESTAMP,
        ),
    )
    provider.save_state(wallet_id, account_id, trading_state)


def seed_account_trading_with_trades(
    provider: collection_providers.AccountTradingProvider,
    wallet_id: str,
    account_id: str,
    raw_trades: list[dict],
) -> None:
    protocol_trades = [
        trades_protocol.to_protocol_trade(raw_trade)
        for raw_trade in raw_trades
    ]
    trading_state = protocol_models.AccountTradingState(
        version=sync_constants.USER_ACCOUNTS_TRADING_STATE_VERSION,
        account_trading=protocol_models.AccountTrading(
            updated_at=_TEST_TIMESTAMP,
            trades=protocol_trades,
        ),
    )
    provider.save_state(wallet_id, account_id, trading_state)


async def seed_daily_prices_cache(
    data_root: str,
    exchange_name: str,
    symbol: str,
    day_timestamp: int,
    close_price: float,
    *,
    exchange_type: str = trading_enums.ExchangeTypes.SPOT.value,
    sandboxed: bool = False,
) -> None:
    await trading_api.merge_daily_prices(
        exchange_name,
        exchange_type,
        sandboxed,
        symbol,
        {str(day_timestamp): close_price},
        data_root,
    )


def load_account_trading(wallet_id: str, account_id: str) -> protocol_models.AccountTrading:
    trading_state = collection_providers.AccountTradingProvider.instance().load_state(wallet_id, account_id)
    return trading_state.account_trading


async def load_daily_prices_from_root(
    data_root,
    exchange_name: str,
    exchange_type: str,
    sandboxed: bool,
) -> dict:
    return await trading_api.load_daily_prices(exchange_name, exchange_type, sandboxed, data_root)


async def _empty_historical_ohlcv(*_args, **_kwargs):
    if False:
        yield []


@contextlib.contextmanager
def portfolio_history_test_environment(
    tmp_path,
    *,
    exchange_manager_by_account_id: dict[str, exchange_manager_module.ExchangeManager],
    wallet_id: str = _TEST_WALLET_ID,
):
    trading_provider = collection_providers.AccountTradingProvider(base_folder=str(tmp_path))

    @contextlib.asynccontextmanager
    async def fake_exchange_manager(exchange_data, *_args, **_kwargs):
        account_id = exchange_data.auth_details.api_key
        exchange_manager = exchange_manager_by_account_id[account_id]
        yield exchange_manager

    with (
        _patch_wallet(),
        mock.patch.object(
            collection_providers.AccountTradingProvider,
            "instance",
            return_value=trading_provider,
        ),
        mock.patch.object(
            portfolio_history_job_module.trading_exchanges,
            "exchange_manager_from_exchange_data",
            fake_exchange_manager,
        ),
        mock.patch.object(
            portfolio_history_job_module.tentacles_manager_api,
            "get_full_tentacles_setup_config",
            return_value=mock.Mock(),
        ),
        mock.patch.object(
            portfolio_history_job_module.trades_repository_module.TradesRepository,
            "ensure_temporary_trades_channel",
            trades_repository_test_util.ensure_trades_channel,
        ),
        mock.patch.object(
            daily_price_cache_updater_module.exchange_util,
            "get_historical_ohlcv",
            _empty_historical_ohlcv,
        ),
    ):
        yield trading_provider
