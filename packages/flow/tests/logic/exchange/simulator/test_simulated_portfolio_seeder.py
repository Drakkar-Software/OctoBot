#  Drakkar-Software OctoBot-Flow

import datetime

import mock

import octobot_commons.constants as commons_constants
import octobot_protocol.models as protocol_models

import octobot_flow.logic.exchange.simulator.simulated_portfolio_seeder as simulated_portfolio_seeder_module


_TEST_TIMESTAMP = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=datetime.UTC)


class TestSeedSimulatedPortfolio:
    def test_seeds_portfolio_from_account_assets(self):
        account = protocol_models.Account(
            id="sim-account-1",
            name="Simulated",
            is_simulated=True,
            created_at=_TEST_TIMESTAMP,
            updated_at=_TEST_TIMESTAMP,
            assets=[
                protocol_models.DetailedAssetsForTradingType(
                    trading_type=protocol_models.TradingType.SPOT,
                    assets=[
                        protocol_models.DetailedAsset(
                            symbol="USDT",
                            total=1000.0,
                            available=900.0,
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
        portfolio_manager = mock.Mock()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        simulated_portfolio_seeder_module.seed_simulated_portfolio(exchange_manager, account)
        portfolio_manager.apply_forced_portfolio.assert_called_once_with(
            {
                "USDT": {
                    commons_constants.PORTFOLIO_AVAILABLE: 900.0,
                    commons_constants.PORTFOLIO_TOTAL: 1000.0,
                },
            },
            update_available_funds_from_open_orders=True,
        )

    def test_skips_when_account_has_no_assets(self):
        account = protocol_models.Account(
            id="sim-account-2",
            name="Simulated empty",
            is_simulated=True,
            created_at=_TEST_TIMESTAMP,
            updated_at=_TEST_TIMESTAMP,
            specifics=protocol_models.AccountSpecifics(
                actual_instance=protocol_models.GenericAccount(
                    account_type=protocol_models.AccountType.GENERIC,
                ),
            ),
        )
        portfolio_manager = mock.Mock()
        exchange_manager = mock.Mock()
        exchange_manager.exchange_personal_data.portfolio_manager = portfolio_manager
        simulated_portfolio_seeder_module.seed_simulated_portfolio(exchange_manager, account)
        portfolio_manager.apply_forced_portfolio.assert_not_called()
