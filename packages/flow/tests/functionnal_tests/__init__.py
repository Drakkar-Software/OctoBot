import contextlib
import decimal
import mock
import pytest
import time
import os
import typing
import json

# force env var
os.environ["USE_MINIMAL_LIBS"] = "true"
os.environ["ALLOW_FUNDS_TRANSFER"] = "True"

import ccxt.async_support as ccxt_async
import octobot_trading.exchanges.connectors.ccxt.ccxt_clients_cache as ccxt_clients_cache
import octobot.community as community
import octobot.community.local_authenticator as local_community_auth

import octobot_protocol.models as protocol_models

import octobot_copy.constants as copy_constants
import octobot_copy.entities as copy_entities

import octobot_flow.entities
import octobot_flow.jobs
import octobot_flow.environment
import octobot_flow.repositories.community
import octobot_flow.logic.actions.actions_factory as actions_factory

AUTHENTICATED_TEST_GROUP = "authenticated_xdist_group"

# Passed as copy_exchange_account(strategy_id=...) in functional DSL so copy-trading dependencies resolve.
FUNCTIONAL_TEST_COPY_STRATEGY_ID = "functional_test_copy_strategy"


def d_order_price(value: typing.Union[int, float, decimal.Decimal]) -> decimal.Decimal:
    """Exact decimal view of a stored order price (avoids float + int mix in assertions)."""
    if isinstance(value, decimal.Decimal):
        return value
    return decimal.Decimal(str(value))


def set_emit_signals_metadata(automation_state: dict, emit_signals: bool) -> None:
    automation_state["automation"]["metadata"]["emit_signals"] = emit_signals


@contextlib.contextmanager
def trading_signal_emission_patches(emit_signals: bool, *, mock_authenticator: bool = True):
    with contextlib.ExitStack() as stack:
        insert_mock = stack.enter_context(
            mock.patch.object(
                octobot_flow.repositories.community.TradingSignalsRepository,
                "insert_trading_signal",
                mock.AsyncMock(),
            )
        )
        if emit_signals and mock_authenticator:

            @contextlib.asynccontextmanager
            async def _fake_maybe_authenticator(self):
                yield mock.MagicMock()

            stack.enter_context(
                mock.patch.object(
                    octobot_flow.jobs.AutomationJob,
                    "_maybe_authenticator",
                    _fake_maybe_authenticator,
                )
            )
        yield insert_mock


def assert_emitted_signal_account_allocation_ratios(
    copied_account: protocol_models.CopiedAccount,
    *,
    allow_zero_ratio_assets: frozenset[str] = frozenset(),
    allow_negligible_ratio_assets: frozenset[str] = frozenset(),
) -> None:
    """Allocation checks for ``TradingSignal.account.copied_assets`` from ``insert_trading_signal`` only."""
    total_value = decimal.Decimal(0)
    for asset in copied_account.copied_assets or []:
        ratio = decimal.Decimal(str(asset.ratio))
        total_value += ratio
        ratio_float = float(ratio)
        name = asset.name
        if name in allow_zero_ratio_assets:
            assert ratio_float == pytest.approx(0.0, abs=1e-18)
        elif name in allow_negligible_ratio_assets:
            assert ratio_float < 0.05, f"{name} expected negligible ratio, got {ratio_float}"
        else:
            assert ratio_float > 0, f"{name} ratio should be > 0, got {ratio_float}"
    assert float(total_value) == pytest.approx(1.0, abs=1e-3)


def is_on_github_ci():
    # Always set to true when GitHub Actions is running the workflow.
    # You can use this variable to differentiate when tests are being run locally or by GitHub Actions.
    # from https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/store-information-in-variables
    return bool(os.getenv("GITHUB_ACTIONS"))

current_time = time.time()
EXCHANGE_INTERNAL_NAME = "binanceus" if is_on_github_ci() else "binance" # binanceus works on github CI


async def fetch_last_price(symbol: str) -> float:
    exchange_class = getattr(ccxt_async, EXCHANGE_INTERNAL_NAME)
    exchange = exchange_class({})
    try:
        ticker = await exchange.fetch_ticker(symbol)
    finally:
        await exchange.close()
    last = ticker.get("last") or ticker.get("close")
    if last is None:
        raise AssertionError(f"{symbol} ticker has no last or close price")
    return float(last)


@contextlib.contextmanager
def mocked_local_user_configuration():
    with mock.patch.object(
        local_community_auth,
        "get_user_configuration",
        local_community_auth.get_stateless_configuration,
    ):
        yield


@contextlib.contextmanager
def mocked_community_authentication():
    with contextlib.ExitStack() as stack:
        stack.enter_context(mocked_local_user_configuration())
        login_mock = stack.enter_context(
            mock.patch.object(
                community.CommunityAuthentication, "login", mock.AsyncMock(),
            )
        )
        stack.enter_context(
            mock.patch.object(
                community.CommunityAuthentication,
                "is_logged_in",
                mock.AsyncMock(return_value=True),
            )
        )
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
                "exchange_account_elements": {
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
            "exchange_account_elements": {
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


def copy_exchange_account_action(
    reference_market: str,
    reference_account: protocol_models.CopiedAccount,
    account_copy_settings: typing.Optional[copy_entities.AccountCopySettings] = None,
    strategy_id: str = FUNCTIONAL_TEST_COPY_STRATEGY_ID,
) -> dict:
    return {
        "id": "action_copy_exchange_account",
        "dsl_script": actions_factory.create_copy_exchange_account_action(
            strategy_id, reference_market, reference_account, account_copy_settings
        ).dsl_script,
    }


def empty_copy_exchange_account_action(
    strategy_id: str = FUNCTIONAL_TEST_COPY_STRATEGY_ID,
) -> dict:
    """Copy action with empty reference fields until a trading signal fills the DSL (refresh_required)."""
    return {
        "id": "action_copy_exchange_account",
        "dsl_script": (
            f"copy_exchange_account(strategy_id={json.dumps(strategy_id)}, reference_market='', reference_account='')"
        ),
    }


@pytest.fixture
def isolated_exchange_cache():
    with ccxt_clients_cache.isolated_empty_cache():
        yield


def automation_state_dict(
    resolved_actions: list[octobot_flow.entities.AbstractActionDetails],
) -> dict[str, typing.Any]:
    return {
        "automation": {
            "metadata": {"automation_id": "automation_1"},
            "actions_dag": {"actions": resolved_actions}
        }
    }


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
