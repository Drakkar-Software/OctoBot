#  Drakkar-Software OctoBot-Flow



import datetime

import decimal



import mock

import pytest



import octobot_commons.constants as commons_constants

import octobot_protocol.models as protocol_models

import octobot_trading.api as trading_api

import octobot_trading.constants as trading_constants

import octobot_trading.enums as trading_enums

import octobot_trading.errors as trading_errors

import octobot_trading.personal_data as personal_data



import octobot_flow.logic.exchange.simulator.simulated_portfolio_seeder as simulated_portfolio_seeder_module

import octobot_flow.logic.global_view.exchange_account_refresh as exchange_account_refresh_module

import octobot_flow.repositories.exchange.tickers_repository as tickers_repository_module

from tests.logic.global_view.portfolio_test_util import wire_portfolio_pipeline

from tests.logic.global_view.portfolio_test_util import wire_repository_factory





def _open_order_dict(exchange_id: str, symbol: str) -> dict:

    return {

        trading_constants.STORAGE_ORIGIN_VALUE: {

            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_id,

            trading_enums.ExchangeConstantsOrderColumns.SYMBOL.value: symbol,

            trading_enums.ExchangeConstantsOrderColumns.FILLED.value: 0,

        }

    }





def _portfolio_content() -> dict:

    return {

        "USDT": {

            commons_constants.PORTFOLIO_TOTAL: 1000.0,

            commons_constants.PORTFOLIO_AVAILABLE: 1000.0,

        },

        "BTC": {

            commons_constants.PORTFOLIO_TOTAL: 0.1,

            commons_constants.PORTFOLIO_AVAILABLE: 0.1,

        },

    }





def _wire_portfolio_pipeline(exchange_manager, portfolio_content: dict, **kwargs) -> None:

    wire_portfolio_pipeline(exchange_manager, portfolio_content, **kwargs)





def _patch_repository_factory(exchange_manager, balance_content: dict, **kwargs):

    factory, portfolio_repository, orders_repository, tickers_repository = wire_repository_factory(

        exchange_manager,

        balance_content,

        **kwargs,

    )

    factory_patch = mock.patch.object(

        exchange_account_refresh_module,

        "_create_exchange_repository_factory",

        mock.Mock(return_value=factory),

    )

    return factory_patch, factory, portfolio_repository, orders_repository, tickers_repository





class TestRefreshExchangeAccountPortfolio:

    @pytest.mark.asyncio

    async def test_real_refresh_applies_balance_to_portfolio_manager(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, {})

        factory_patch, _factory, portfolio_repository, orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        ensure_ticker_channel_mock = mock.AsyncMock()

        refresh_valuation_mock = mock.Mock()

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                ensure_ticker_channel_mock,

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                refresh_valuation_mock,

            ),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        portfolio_repository.fetch_and_apply_portfolio.assert_awaited_once()

        orders_repository.fetch_open_orders.assert_not_called()

        exchange_manager.exchange_personal_data.handle_portfolio_update.assert_awaited_once()

        applied_balance = exchange_manager.exchange_personal_data.handle_portfolio_update.await_args.args[0]

        assert applied_balance["BTC"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("0.1")

        assert applied_balance["USDT"][commons_constants.PORTFOLIO_TOTAL] == decimal.Decimal("1000.0")

        asset_symbols = {

            asset.symbol

            for assets_for_trading_type in refresh_result.assets

            for asset in assets_for_trading_type.assets

        }

        assert asset_symbols == {"USDT", "BTC"}



    @pytest.mark.asyncio

    async def test_real_refresh_without_handle_portfolio_update_would_fail(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, {}, portfolio_total=0.0)

        exchange_manager.exchange_personal_data.handle_portfolio_update = mock.AsyncMock(return_value=False)

        factory, portfolio_repository, _orders_repository, _tickers_repository = wire_repository_factory(

            exchange_manager,

            balance_content,

        )

        portfolio_repository.fetch_and_apply_portfolio = mock.AsyncMock(return_value=balance_content)

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                mock.Mock(),

            ),

            mock.patch.object(

                exchange_account_refresh_module,

                "_create_exchange_repository_factory",

                mock.Mock(return_value=factory),

            ),

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        assert refresh_result.assets == []

        assert refresh_result.ticker_closes == {}



    @pytest.mark.asyncio

    async def test_simulated_refresh_uses_seeded_account_assets(self):

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(

            exchange_manager,

            {

                "USDC": {

                    commons_constants.PORTFOLIO_TOTAL: 1000.0,

                    commons_constants.PORTFOLIO_AVAILABLE: 1000.0,

                },

            },

            portfolio_total=1000.0,

        )

        portfolio_manager = exchange_manager.exchange_personal_data.portfolio_manager

        portfolio_manager.apply_forced_portfolio = mock.Mock(

            side_effect=lambda portfolio_content, update_available_funds_from_open_orders=False: (

                portfolio_manager.handle_balance_update(portfolio_content)

            ),

        )

        account = protocol_models.Account(

            id="sim-account-1",

            name="Simulated",

            is_simulated=True,

            created_at=datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC),

            updated_at=datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC),

            assets=[

                protocol_models.DetailedAssetsForTradingType(

                    trading_type=protocol_models.TradingType.SPOT,

                    assets=[

                        protocol_models.DetailedAsset(

                            symbol="USDC",

                            total=1000.0,

                            available=1000.0,

                        ),

                    ],

                ),

            ],

            specifics=protocol_models.AccountSpecifics(

                actual_instance=protocol_models.ExchangeAccount(

                    account_type=protocol_models.AccountType.EXCHANGE,

                    remote_account_id="sim-account-1",

                    exchange_config_ids=["exchange-config-1"],

                ),

            ),

        )

        simulated_portfolio_seeder_module.seed_simulated_portfolio(exchange_manager, account)

        fetch_tickers_mock = mock.AsyncMock(return_value={})

        create_factory_mock = mock.Mock()

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(

                exchange_account_refresh_module,

                "_fetch_tickers",

                fetch_tickers_mock,

            ),

            mock.patch.object(

                exchange_account_refresh_module,

                "_create_exchange_repository_factory",

                create_factory_mock,

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                mock.Mock(),

            ),

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                is_simulated=True,

                previous_open_orders=[],

            )



        fetch_tickers_mock.assert_awaited_once_with(exchange_manager, [])

        create_factory_mock.assert_not_called()



        portfolio_manager.apply_forced_portfolio.assert_called_once()

        asset_symbols = {

            asset.symbol

            for assets_for_trading_type in refresh_result.assets

            for asset in assets_for_trading_type.assets

        }

        assert "USDC" in asset_symbols



    @pytest.mark.asyncio

    async def test_real_refresh_portfolio_total_positive_with_ticker_prices(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content, portfolio_total=6000.0)

        factory_patch, _factory, _portfolio_repository, _orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                mock.Mock(),

            ),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        assert isinstance(refresh_result.ticker_closes, dict)





class TestRefreshExchangeAccountRepositoryBranches:

    @pytest.mark.asyncio

    async def test_fetch_open_orders_false_skips_orders_repository(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content)

        factory_patch, _factory, portfolio_repository, orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(personal_data, "refresh_portfolio_valuation", mock.Mock()),

            factory_patch,

        ):

            await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        portfolio_repository.fetch_and_apply_portfolio.assert_awaited_once()

        orders_repository.fetch_open_orders.assert_not_called()



    @pytest.mark.asyncio

    async def test_fetch_open_orders_true_fetches_orders_for_symbols(self):

        balance_content = _portfolio_content()

        open_orders = [_open_order_dict("order-1", "ETH/USDT")]

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content)

        factory_patch, _factory, portfolio_repository, orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content, open_orders=open_orders)

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(personal_data, "refresh_portfolio_valuation", mock.Mock()),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=True,

                open_order_symbols=["ETH/USDT"],

            )



        portfolio_repository.fetch_and_apply_portfolio.assert_awaited_once()

        orders_repository.fetch_open_orders.assert_awaited_once_with(["ETH/USDT"])

        assert refresh_result.open_orders == open_orders



    @pytest.mark.asyncio

    async def test_orders_not_supported_returns_empty_open_orders(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content)

        factory_patch, _factory, _portfolio_repository, orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        orders_repository.fetch_open_orders = mock.AsyncMock(

            side_effect=trading_errors.NotSupported("unsupported"),

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(personal_data, "refresh_portfolio_valuation", mock.Mock()),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=True,

                open_order_symbols=["ETH/USDT"],

            )



        assert refresh_result.open_orders == []





class TestDetectChangedOrderIds:

    @pytest.mark.asyncio

    async def test_returns_disappeared_order_ids(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content)

        current_orders = [_open_order_dict("order-2", "ETH/USDT")]

        factory_patch, _factory, _portfolio_repository, _orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content, open_orders=current_orders)

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(personal_data, "refresh_portfolio_valuation", mock.Mock()),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                {"order-1", "order-2"},

                fetch_open_orders=True,

                open_order_symbols=["ETH/USDT"],

            )



        assert refresh_result.changed_order_ids == {"order-1"}



    @pytest.mark.asyncio

    async def test_returns_empty_when_no_previous_orders(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(exchange_manager, balance_content)

        factory_patch, _factory, _portfolio_repository, _orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(personal_data, "refresh_portfolio_valuation", mock.Mock()),

            factory_patch,

        ):

            refresh_result = await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        assert refresh_result.changed_order_ids == set()





class TestRefreshExchangeAccountLogging:

    @pytest.mark.asyncio

    async def test_logs_fetched_portfolio_once_at_info(self):

        balance_content = _portfolio_content()

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDC")

        exchange_manager.exchange_personal_data = mock.Mock()

        _wire_portfolio_pipeline(

            exchange_manager, balance_content, portfolio_total=6000.0, exchange_name="binance",

        )

        factory_patch, _factory, _portfolio_repository, _orders_repository, _tickers_repository = (

            _patch_repository_factory(exchange_manager, balance_content)

        )

        logger_mock = mock.Mock()

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                mock.Mock(),

            ),

            factory_patch,

            mock.patch.object(

                exchange_account_refresh_module,

                "_get_logger",

                return_value=logger_mock,

            ),

        ):

            await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                fetch_open_orders=False,

            )



        portfolio_log_calls = [

            call_args

            for call_args in logger_mock.info.call_args_list

            if call_args.args and call_args.args[0] == "Fetched [%s] full [%s] portfolio: %s"

        ]

        assert len(portfolio_log_calls) == 1

        assert portfolio_log_calls[0].args[1] == "binance"

        assert portfolio_log_calls[0].args[2] == "real"





class TestSimulatedTickerFetchMerge:

    @pytest.mark.asyncio

    async def test_fetches_order_and_valuation_symbols_once(self):

        exchange_manager = mock.Mock()

        exchange_manager.exchange.get_option_value = mock.Mock(return_value="USDT")

        portfolio_content = _portfolio_content()

        _wire_portfolio_pipeline(exchange_manager, portfolio_content, exchange_name="bitmart")

        open_order = _open_order_dict("order-1", "ETH/USDT")

        fetch_tickers_mock = mock.AsyncMock(return_value={

            "ETH/USDT": {trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 3000},

            "BTC/USDT": {trading_enums.ExchangeConstantsTickersColumns.CLOSE.value: 50000},

        })

        with (

            mock.patch.object(

                tickers_repository_module.TickersRepository,

                "ensure_temporary_ticker_channel",

                mock.AsyncMock(),

            ),

            mock.patch.object(

                trading_api,

                "get_portfolio",

                return_value=portfolio_content,

            ),

            mock.patch.object(

                personal_data,

                "valuation_symbols_from_portfolio",

                side_effect=[["BTC/USDT"], ["BTC/USDT"]],

            ),

            mock.patch.object(

                exchange_account_refresh_module,

                "_fetch_tickers",

                fetch_tickers_mock,

            ),

            mock.patch.object(

                personal_data,

                "refresh_portfolio_valuation",

                mock.Mock(),

            ),

        ):

            await exchange_account_refresh_module.refresh_exchange_account(

                exchange_manager,

                protocol_models.TradingType.SPOT,

                set(),

                is_simulated=True,

                previous_open_orders=[open_order],

            )



        fetch_tickers_mock.assert_awaited_once()

        fetched_symbols = fetch_tickers_mock.await_args.args[1]

        assert set(fetched_symbols) == {"BTC/USDT", "ETH/USDT"}


