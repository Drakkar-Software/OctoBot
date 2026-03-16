import contextlib
import mock
import pytest
import time
import os
import typing

# force env var
os.environ["USE_MINIMAL_LIBS"] = "true"
os.environ["ALLOW_FUNDS_TRANSFER"] = "True"

import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache
import octobot.community as community

import octobot_flow.entities

import octobot_flow.environment
import octobot_flow.repositories.community


current_time = time.time()
EXCHANGE_INTERNAL_NAME = "binance"

@contextlib.contextmanager
def mocked_community_authentication():
    with mock.patch.object(
        community.CommunityAuthentication, "login", mock.AsyncMock(),
    ) as login_mock, mock.patch.object(
        community.CommunityAuthentication, "is_logged_in", mock.AsyncMock(return_value=True)
    ):
        yield login_mock


@contextlib.contextmanager
def mocked_community_repository():
    with mock.patch.object(
        octobot_flow.repositories.community.CommunityRepository, "insert_bot_logs", mock.AsyncMock()
    ) as insert_bot_logs_mock:
        yield insert_bot_logs_mock

# ensure environment is initialized
octobot_flow.environment.initialize_environment()


@pytest.fixture
def global_state():
    return {
        "exchange_account_details": {
            "exchange_details": {
                "internal_name": EXCHANGE_INTERNAL_NAME,
            },
            # "auth_details": {}, # not needed for simulator
            # "portfolio": {}, # irrelevant for simulator
        },
        "automation": {
                # "profile_data": {
                #     "profile_details": {
                #         "id": "bot_1",
                #         "bot_id": "id:bot_1",
                #     },
                #     "crypto_currencies": [
                #         {"trading_pairs": ["BTC/USDT"], "name": "BTC"},
                #         {"trading_pairs": ["ETH/USDT"], "name": "ETH"},
                #     ],
                #     "trading": {
                #         "reference_market": "USDT",
                #     },
                #     "exchanges": [
                #         {
                #             "internal_name": EXCHANGE_INTERNAL_NAME,
                #             "exchange_type": "spot",
                #         }
                #     ],
                #     "trader": {
                #         "enabled": False,
                #     },
                #     "trader_simulator": {
                #         "enabled": True,
                #     },
                #     "tentacles": [
                #         {
                #             "name": "IndexTradingMode",
                #             "config": {
                #                 "required_strategies": [],
                #                 "refresh_interval": 1,
                #                 "rebalance_trigger_min_percent": 5,
                #                 "sell_unindexed_traded_coins": True,
                #                 "quote_asset_rebalance_trigger_min_percent": 20,
                #                 "index_content": [
                #                     {"name": "BTC", "value": 1},
                #                     {"name": "ETH", "value": 1},
                #                 ]
                #             }
                #         },
                #     ]
                # },
                "metadata": {
                    "automation_id": "automation_1",
                },
                "client_exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "USDT": {
                                "available": 1000.0,
                                "total": 1000.0,
                            },
                            "ETH": {
                                "available": 0.1,
                                "total": 0.1,
                            },
                        },
                    },
                },
                "execution": {
                    "previous_execution": {
                        "trigger_time": current_time - 600,
                        "trigger_reason": "scheduled",
                        # "additional_actions": {}, # no additional actions
                        "strategy_execution_time": current_time - 590,
                    },
                    "current_execution": {
                        "trigger_reason": "scheduled",
                        # "additional_actions": {}, # no additional actions
                    },
                    # "degraded_state": {} # no degraded state
                    "execution_error": None # no execution error
                },
                # "exchange_account_elements": {
                #     "portfolio": {
                #         "initial_value": 3000,
                #         "content": {
                #             # should trigger a rebalance: this does not follow the index config
                #             "USDT": {
                #                 "available": 1000.0,
                #                 "total": 1000.0,
                #             },
                #             "ETH": {
                #                 "available": 0.1,
                #                 "total": 0.1,
                #             },
                #         }
                #         # "full_content": {} # irrelevant for simulator
                #         # "asset_values": {} # cleared after iteration
                #     },
                #     "orders": {}, # no open orders
                #     "positions": {}, # no positions
                #     "trades": [], # no trades
                # }
                # "post_actions": {}, # no post actions
            },
    }


@pytest.fixture
def btc_usdc_global_state():
    return {
        "exchange_account_details": {
            "exchange_details": {
                "internal_name": EXCHANGE_INTERNAL_NAME,
            },
        },
        "automation": {
            "metadata": {
                "automation_id": "automation_1",
            },
            "client_exchange_account_elements": {
                    "portfolio": {
                        "content": {
                            "USDC": {
                                "available": 1000.0,
                                "total": 1000.0,
                            },
                            "BTC": {
                                "available": 0.1,
                                "total": 0.1,
                            },
                        },
                    },
                },
                "execution": {
                    "previous_execution": {
                        "trigger_time": current_time - 600,
                        "trigger_reason": "scheduled",
                        "strategy_execution_time": current_time - 590,
                    },
                    "current_execution": {
                        "trigger_reason": "scheduled",
                    },
                },
            },
    }


@pytest.fixture
def auth_details():
    return octobot_flow.entities.UserAuthentication(
        email="test@test.com",
        password="test_password",
        hidden=True,
    )


@pytest.fixture
def actions_with_market_orders():
    return [
        {
            "id": "action_1",
            "dsl_script": "market('buy', 'BTC/USDT', '20q')",
        },
        {
            "id": "action_2",
            "dsl_script": "market('buy', 'BTC/USDT', '10q')",
        },
    ]


@pytest.fixture
def actions_with_create_limit_orders():
    return [
        {
            "id": "action_1",
            "dsl_script": "limit('buy', 'BTC/USDC', '10q', '-20%')",
        }
    ]


@pytest.fixture
def actions_with_cancel_limit_orders():
    return [
        {
            "id": "action_1",
            "dsl_script": "cancel_order('BTC/USDC')",
        }
    ]


@pytest.fixture
def isolated_exchange_cache():
    with ccxt_clients_cache.isolated_empty_cache():
        yield


def automation_state_dict(resolved_actions: list[octobot_flow.entities.AbstractActionDetails]) -> dict[str, typing.Any]:
    return {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": resolved_actions}
        }
    }


automations_state_dict = automation_state_dict  # alias for backward compatibility


def resolved_actions(actions: list[dict[str, typing.Any]]) -> list[octobot_flow.entities.AbstractActionDetails]:
    dag = octobot_flow.entities.ActionsDAG(
        actions=[octobot_flow.entities.parse_action_details(action) for action in actions],
    )
    return dag.actions


def create_wait_action(min_delay: float, max_delay: float, id: str = "action_wait", dependencies: list[dict[str, typing.Any]] = []) -> dict[str, typing.Any]:
    return {
        "id": id,
        "dsl_script": f"wait({min_delay}, {max_delay}, return_remaining_time=True)",
        "dependencies": dependencies,
    }
