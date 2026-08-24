#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.
import asyncio
import postgrest

import pytest
import pytest_asyncio
import mock

import octobot.community as community
import octobot.community.authentication
import octobot.community.models.community_user_account as community_user_account
import octobot.constants as constants
import octobot_commons.authentication as authentication
import octobot_commons.configuration
import octobot_commons.profiles.profile_data

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

AUTH_URL = "https://oh.fake/auth"
_TEST_SYNC_URL = "https://test-sync.example"
AUTH_RETURN = {
    "access_token": "1",
    "refresh_token": "2",
    "expires_in": 3600,
}
EMAIL_RETURN = {
    "email": "plop"
}
AUTH_HEADER_RETURN = {
    community.CommunityAuthentication.SESSION_HEADER: "helloooo",
}


class MockedResponse:
    def __init__(self, status_code=200, json=None, headers={}):
        self.status_code = status_code
        self.json_resp = json
        self.headers = headers

    def json(self):
        return self.json_resp


@pytest.fixture
def auth():
    community.IdentifiersProvider.use_production()
    authenticator = community.CommunityAuthentication()
    authenticator.supabase_client = mock.Mock(
        sign_in=mock.AsyncMock(),
        sign_in_with_otp_token=mock.AsyncMock(),
        sign_out=mock.AsyncMock(),
        auth=mock.Mock(_storage_key="_storage_key"),
        aclose=mock.AsyncMock(),
    )
    return authenticator


@pytest_asyncio.fixture
async def logged_in_auth(auth):
    auth.user_account.has_user_data = mock.Mock(return_value=True)
    auth.user_account.get_email = mock.Mock(return_value="plop")
    return auth


def test_constructor():
    with mock.patch.object(community.CommunityAuthentication, "login", mock.Mock()) as login_mock:
        community.IdentifiersProvider.use_production()
        community.CommunityAuthentication()
        auth = community.CommunityAuthentication()
        login_mock.assert_not_called()
        assert not auth.user_account.supports.is_supporting()
        assert auth.initialized_event is None


@pytest.mark.asyncio
async def test_login(auth):
    resp_mock = mock.Mock()
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
            mock.patch.object(community.CommunityAuthentication, "_ensure_community_url", mock.Mock()) \
                    as _ensure_community_url_mock, \
            mock.patch.object(community.CommunityAuthentication, "_ensure_email", mock.Mock()) \
                    as _ensure_email_mock, \
            mock.patch.object(community.CommunityAuthentication, "_on_account_updated", mock.AsyncMock()) \
                    as _on_account_updated_mock, \
            mock.patch.object(community.CommunityAuthentication, "is_logged_in", mock.Mock()) \
                    as is_logged_in_mock, \
            mock.patch.object(community.CommunityAuthentication, "on_signed_in", mock.AsyncMock()) \
                    as on_signed_in_mock:
        await auth.login("username", "password")
        reset_mock.assert_called_once()
        _ensure_community_url_mock.assert_called_once()
        _ensure_email_mock.assert_called_once()
        _on_account_updated_mock.assert_called_once()
        is_logged_in_mock.assert_called_once()
        on_signed_in_mock.assert_called_once()
        auth.supabase_client.sign_in.assert_awaited_once_with("username", "password")
        auth.supabase_client.sign_in_with_otp_token.assert_not_called()
        auth.supabase_client.sign_in.reset_mock()
        await auth.login(None, None, password_token="password_t")
        auth.supabase_client.sign_in.assert_not_called()
        auth.supabase_client.sign_in_with_otp_token.assert_awaited_once_with("password_t")


async def test_fetch_bot_profile_data_without_tentacles_options(auth):
    FETCHED_PROFILE_USD_LIKE = {
        "bot_id": "53e0dc3e-3cbe-476d-9bda-b30bc4941fb4",
        "bot": {"user_id": "3330dc3e-3cbe-476d-9bda-b30bc4941fb4", "created_at": "2024-08-14T22:13:22.1111+04:00"},
        "exchanges": [],
        "exchange_account_id": "exchange_account_id_123",
        "is_simulated": True, "created_at": "2023-08-14T22:13:22.466399+04:00",
        "options": {"portfolio": [{"asset": "USD-like", "value": 1000}]}, "product_config": {"config": {
            "backtesting_context": {"exchanges": ["mexc"], "start_time_delta": 15552000,
                                    "starting_portfolio": {"USDT": 3000}},
            "crypto_currencies": [{"name": "Bitcoin", "trading_pairs": ["BTC/USDT"]}],
            "exchanges": [{"internal_name": "mexc"}], "options": {}, "profile_details": {"name": "serverless"},
            "tentacles": [{"config": {"buy_order_amount": "4%t", "default_config": [None], "enable_health_check": True,
                                      "entry_limit_orders_price_percent": 0.6, "exit_limit_orders_price_percent": 0.5,
                                      "minutes_before_next_buy": 10080, "required_strategies": ["123"],
                                      "secondary_entry_orders_amount": "3%t", "secondary_entry_orders_count": 1,
                                      "secondary_entry_orders_price_percent": 0.5, "secondary_exit_orders_count": 1,
                                      "secondary_exit_orders_price_percent": 0.8,
                                      "trigger_mode": "Maximum evaluators signals based", "use_init_entry_orders": True,
                                      "use_market_entry_orders": False, "use_secondary_entry_orders": True,
                                      "use_secondary_exit_orders": True, "use_stop_losses": False,
                                      "use_take_profit_exit_orders": True}, "name": "DCATradingMode"}, {
                              "config": {"background_social_evaluators": [""], "default_config": [None],
                                         "re_evaluate_TA_when_social_or_realtime_notification": True,
                                         "required_candles_count": 21, "required_evaluators": [""],
                                         "required_time_frames": ["1h"], "social_evaluators_notification_timeout": 3600},
                              "name": "SimpleStrategyEvaluator"},
                          {"config": {"period_length": 9, "price_threshold_percent": 0},
                           "name": "EMAMomentumEvaluator"}], "trader": {"enabled": True}, "trader_simulator": {},
            "trading": {"reference_market": "USD-like", "risk": 0.5}}, "product": {
            "attributes": {"coins": ["BTC", "USDT"], "ease": "Easy", "exchanges": ["mexc"],
                           "minimal_funds": [{"asset": "USD-like", "value": 50}], "risk": "Moderate",
                           "subcategories": ["classic-dca", "popular"], "trading": ["Spot"]}, "slug": "bitcoin-vision", "id": "product_id_123"},
            "version": "0.0.1"}}
    auth.supabase_client = community.CommunitySupabaseClient(
        "https://kfgrrr.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJfffffffHhscnl2bWhka2JyYXJyIiwicm9sZSI6ImFub24iLCJp"
        "YXQiOjE2ODQ2ODcwMTksImV4cCI6MjAwMDI2MzAxOX0.UH0g1ZDr9kDQMkGWxxy29lLjDEIPlSeU_f2GjwFFfGE",
        None
    )
    exchange_data = octobot_commons.profiles.profile_data.ExchangeData(internal_name="mexc")
    with mock.patch.object(postgrest.AsyncQueryRequestBuilder, "execute",
                           mock.AsyncMock(return_value=mock.Mock(data=[FETCHED_PROFILE_USD_LIKE]))) as execute_mock, \
            mock.patch.object(auth.supabase_client, "_fetch_full_exchange_configs",
                              mock.AsyncMock(return_value=([exchange_data], []))) as _fetch_full_exchange_configs_mock:
        parsed_data = octobot_commons.profiles.profile_data.ProfileData.from_dict(
            {"backtesting_context": {"exchanges": ["mexc"], "start_time_delta": 15552000,
                                     "starting_portfolio": {"USDT": 3000}, "update_interval": 604800},
             "crypto_currencies": [{"enabled": True, "name": "Bitcoin", "trading_pairs": ["BTC/USDT"]}],
             "exchanges": [{"internal_name": "mexc"}], "future_exchange_data": {"default_leverage": None, "symbol_data": []},
             "options": {"values": {}},
             "profile_details": {
                 "bot_id": None, "id": "bot_id", "name": "bitcoin-vision", "version": "0.0.1",
                 "user_id": '3330dc3e-3cbe-476d-9bda-b30bc4941fb4'
             },
             "tentacles": [{"config": {"buy_order_amount": "4%t", "default_config": [None], "enable_health_check": True,
                                       "entry_limit_orders_price_percent": 0.6, "exit_limit_orders_price_percent": 0.5,
                                       "minutes_before_next_buy": 10080, "required_strategies": ["123"],
                                       "secondary_entry_orders_amount": "3%t", "secondary_entry_orders_count": 1,
                                       "secondary_entry_orders_price_percent": 0.5, "secondary_exit_orders_count": 1,
                                       "secondary_exit_orders_price_percent": 0.8,
                                       "trigger_mode": "Maximum evaluators signals based",
                                       "use_init_entry_orders": True, "use_market_entry_orders": False,
                                       "use_secondary_entry_orders": True, "use_secondary_exit_orders": True,
                                       "use_stop_losses": False, "use_take_profit_exit_orders": True},
                            "name": "DCATradingMode"}, {
                               "config": {"background_social_evaluators": [""], "default_config": [None],
                                          "re_evaluate_TA_when_social_or_realtime_notification": True,
                                          "required_candles_count": 21, "required_evaluators": [""],
                                          "required_time_frames": ["1h"],
                                          "social_evaluators_notification_timeout": 3600},
                               "name": "SimpleStrategyEvaluator"},
                           {"config": {"period_length": 9, "price_threshold_percent": 0},
                            "name": "EMAMomentumEvaluator"}], "trader": {"enabled": True},
             "trader_simulator": {"enabled": True, "maker_fees": 0.1, "starting_portfolio": {"USDC": 1000},
                                  "taker_fees": 0.1},
             "trading": {"minimal_funds": [{"asset": "USD-like", "available": 50, "total": 50}],
                         "reference_market": "USDC", "risk": 0.5, "sub_portfolio": {'USDC': 1000},
                         "sellable_assets": None}}
        )
        executed_product_details = community.ExecutedProductDetails(
            product_id="product_id_123",
            started_at=1723659202.1111, # not nested config: use bot created_at (2024-08-14T22:13:22.1111+04:00)
        )
        assert await auth.supabase_client.fetch_bot_profile_data("bot_id", {"mexc": "USDC"}) == (
            parsed_data, executed_product_details
        )
        execute_mock.assert_called_once()
        _fetch_full_exchange_configs_mock.assert_called_once()


async def test_fetch_bot_profile_data_with_tentacles_options(auth):
    FETCHED_PROFILE = {
        "bot_id": "53e0dc3e-3cbe-476d-9bda-b30bc4941fb4",
        "bot": {"user_id": "3330dc3e-3cbe-476d-9bda-b30bc4941fb4", "created_at": "2024-08-14T22:13:22.1111+08:00"},
        "exchanges": [
            {"exchange_credential_id": "30ee7b12-3415-4ce4-b050-80d8bf4548be"}], "is_simulated": True,
        "created_at": "2023-08-14T22:13:22.466399+08:00",
        "options": {
            "portfolio": [{"asset": "USDT", "value": 2000}],
            "sellable_assets": ["USDT", "EUR", "ETH"],
            "tentacles": [
                {"config": {"buy_order_amount": "10%t"}, "name": "DCATradingMode"},
                {"config": {"period_length": 11, "price_threshold_percent": 1222}, "name": "EMAMomentumEvaluator"},
            ],
        },
        "product_config": {"config": {
            "backtesting_context": {"exchanges": ["mexc"], "start_time_delta": 15552000,
                                    "starting_portfolio": {"USDT": 3000}},
            "crypto_currencies": [{"name": "Bitcoin", "trading_pairs": ["BTC/USDT"]}],
            "exchanges": [{"internal_name": "mexc"}], "options": {}, "profile_details": {"name": "serverless"},
            "tentacles": [{"config": {"buy_order_amount": "4%t", "default_config": [None], "enable_health_check": True,
                                      "entry_limit_orders_price_percent": 0.6, "exit_limit_orders_price_percent": 0.5,
                                      "minutes_before_next_buy": 10080, "required_strategies": ["123"],
                                      "secondary_entry_orders_amount": "3%t", "secondary_entry_orders_count": 1,
                                      "secondary_entry_orders_price_percent": 0.5, "secondary_exit_orders_count": 1,
                                      "secondary_exit_orders_price_percent": 0.8,
                                      "trigger_mode": "Maximum evaluators signals based", "use_init_entry_orders": True,
                                      "use_market_entry_orders": False, "use_secondary_entry_orders": True,
                                      "use_secondary_exit_orders": True, "use_stop_losses": False,
                                      "use_take_profit_exit_orders": True}, "name": "DCATradingMode"}, {
                              "config": {"background_social_evaluators": [""], "default_config": [None],
                                         "re_evaluate_TA_when_social_or_realtime_notification": True,
                                         "required_candles_count": 21, "required_evaluators": [""],
                                         "required_time_frames": ["1h"], "social_evaluators_notification_timeout": 3600},
                              "name": "SimpleStrategyEvaluator"},
                          {"config": {"period_length": 9, "price_threshold_percent": 0},
                           "name": "EMAMomentumEvaluator"}], "trader": {"enabled": True}, "trader_simulator": {},
            "trading": {"reference_market": "USDT", "risk": 0.5}}, "product": {
            "attributes": {"coins": ["BTC", "USDT"], "ease": "Easy", "exchanges": ["mexc"],
                           "minimal_funds": [{"asset": "USD-like", "value": 50}], "risk": "Moderate",
                           "subcategories": ["classic-dca", "popular"], "trading": ["Spot"]}, "slug": "bitcoin-vision", "id": "product_id_123"},
            "version": "0.0.1"}}
    auth.supabase_client = community.CommunitySupabaseClient(
        "https://kfgrrr.supabase.co",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJfffffffHhscnl2bWhka2JyYXJyIiwicm9sZSI6ImFub24iLCJp"
        "YXQiOjE2ODQ2ODcwMTksImV4cCI6MjAwMDI2MzAxOX0.UH0g1ZDr9kDQMkGWxxy29lLjDEIPlSeU_f2GjwFFfGE",
        None
    )
    with mock.patch.object(postgrest.AsyncQueryRequestBuilder, "execute",
                           mock.AsyncMock(return_value=mock.Mock(data=[FETCHED_PROFILE]))) as execute_mock, \
            mock.patch.object(auth.supabase_client, "_fetch_full_exchange_configs",
                              mock.AsyncMock(return_value=([], []))) as _fetch_full_exchange_configs_mock:
        parsed_data = octobot_commons.profiles.profile_data.ProfileData.from_dict(
            {"backtesting_context": {"exchanges": ["mexc"], "start_time_delta": 15552000,
                                     "starting_portfolio": {"USDT": 3000}, "update_interval": 604800},
             "crypto_currencies": [{"enabled": True, "name": "Bitcoin", "trading_pairs": ["BTC/USDT"]}],
             "exchanges": [], "future_exchange_data": {"default_leverage": None, "symbol_data": []},
             "options": {"values": {}},
             "profile_details": {"bot_id": None, "id": "bot_id", "name": "bitcoin-vision", "version": "0.0.1",
                                 "user_id": "3330dc3e-3cbe-476d-9bda-b30bc4941fb4"},
             "tentacles": [{"config": {"buy_order_amount": "10%t", "default_config": [None], "enable_health_check": True,
                                       "entry_limit_orders_price_percent": 0.6, "exit_limit_orders_price_percent": 0.5,
                                       "minutes_before_next_buy": 10080, "required_strategies": ["123"],
                                       "secondary_entry_orders_amount": "3%t", "secondary_entry_orders_count": 1,
                                       "secondary_entry_orders_price_percent": 0.5, "secondary_exit_orders_count": 1,
                                       "secondary_exit_orders_price_percent": 0.8,
                                       "trigger_mode": "Maximum evaluators signals based",
                                       "use_init_entry_orders": True, "use_market_entry_orders": False,
                                       "use_secondary_entry_orders": True, "use_secondary_exit_orders": True,
                                       "use_stop_losses": False, "use_take_profit_exit_orders": True},
                            "name": "DCATradingMode"}, {
                               "config": {"background_social_evaluators": [""], "default_config": [None],
                                          "re_evaluate_TA_when_social_or_realtime_notification": True,
                                          "required_candles_count": 21, "required_evaluators": [""],
                                          "required_time_frames": ["1h"],
                                          "social_evaluators_notification_timeout": 3600},
                               "name": "SimpleStrategyEvaluator"},
                           {"config": {"period_length": 11, "price_threshold_percent": 1222},
                            "name": "EMAMomentumEvaluator"}], "trader": {"enabled": True},
             "trader_simulator": {"enabled": True, "maker_fees": 0.1, "starting_portfolio": {"USDT": 2000},
                                  "taker_fees": 0.1},
             "trading": {"minimal_funds": [{"asset": "USD-like", "available": 50, "total": 50}],
                         "reference_market": "USDT", "risk": 0.5, "sub_portfolio": {'USDT': 2000},
                         "sellable_assets": ["USDT", "EUR", "ETH"]}}
        )
        executed_product_details = community.ExecutedProductDetails(
            product_id="product_id_123",
            started_at=1723644802.1111, # not nested config: use bot created_at (2024-08-14T22:13:22.1111+08:00)
        )
        assert await auth.supabase_client.fetch_bot_profile_data("bot_id", {}) == (
            parsed_data, executed_product_details
        )
        execute_mock.assert_called_once()
        _fetch_full_exchange_configs_mock.assert_called_once()


async def test_logout(auth):
    with mock.patch.object(community.CommunityAuthentication, "_reset_tokens", mock.Mock()) as reset_mock, \
            mock.patch.object(community.CommunityAuthentication, "remove_login_detail", mock.Mock()) as remove_mock:
        await auth.logout()
        reset_mock.assert_called_once()
        remove_mock.assert_called_once()
        auth.supabase_client.sign_out.assert_called_once()


def test_get_logged_in_email_authenticated(logged_in_auth):
    assert logged_in_auth.get_logged_in_email() == "plop"


def test_get_logged_in_email_unauthenticated(auth):
    with pytest.raises(authentication.AuthenticationRequired):
        auth.get_logged_in_email()


def test_can_authenticate(auth):
    assert auth.can_authenticate() is True


def test_ensure_community_url(auth):
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=False)) as can_authenticate_mock:
        with pytest.raises(authentication.UnavailableError):
            auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()
    with mock.patch.object(auth, "can_authenticate", mock.Mock(return_value=True)) as can_authenticate_mock:
        auth._ensure_community_url()
        can_authenticate_mock.assert_called_once()


def test_is_logged_in(auth):
    auth.user_account.has_user_data = mock.Mock(return_value=False)
    assert auth.is_logged_in() is False
    auth.supabase_client.is_signed_in.assert_called_once()
    auth.user_account.has_user_data.assert_called_once()
    auth.user_account.has_user_data = mock.Mock(return_value=True)
    assert auth.is_logged_in() is True


def test_remove_login_detail(auth):
    with mock.patch.object(auth, "_reset_login_token", mock.Mock()) as _reset_login_token_mock, \
            mock.patch.object(auth, "_save_bot_id", mock.Mock()) as _save_bot_id_mock:
        auth.remove_login_detail()
        _reset_login_token_mock.assert_called_once()
        _save_bot_id_mock.assert_called_once()


def test_reset_login_token(auth):
    with mock.patch.object(octobot_commons.configuration.Configuration, "save", mock.Mock()) as save_mock:
        auth.configuration_storage.set_configuration(
            octobot_commons.configuration.Configuration("", "")
        )
        auth.configuration_storage.sync_storage._configuration.config = {
            constants.CONFIG_COMMUNITY: {
                "_storage_key": "plop"
            }
        }
        auth._reset_login_token()
        assert auth.configuration_storage.sync_storage._configuration.config[constants.CONFIG_COMMUNITY][
                   "_storage_key"] == ""
        save_mock.assert_called_once_with()


def test_get_saved_bot_id(auth):
    assert auth._get_saved_bot_id() is None
    auth.configuration_storage.set_configuration(
        octobot_commons.configuration.Configuration("", "")
    )
    auth.configuration_storage.sync_storage._configuration.config = {
        constants.CONFIG_COMMUNITY: {
            constants.CONFIG_COMMUNITY_BOT_ID: "bid"
        }
    }
    assert auth._get_saved_bot_id() == "bid"


def test_authenticated(auth):
    @authentication.authenticated
    def mock_func(*_):
        pass

    with mock.patch.object(auth, "ensure_token_validity", mock.Mock()) as ensure_token_validity_mock:
        mock_func(auth)
        ensure_token_validity_mock.assert_called_once()


def test_update_supports(auth):
    with mock.patch.object(community.CommunitySupports, "from_community_dict", mock.Mock()) as from_community_dict_mock:
        auth._update_supports(400, {})
        from_community_dict_mock.assert_not_called()
        auth._update_supports(200, {})
        from_community_dict_mock.assert_called_once_with({})


def test_is_initialized(auth):
    assert auth.is_initialized() is False
    auth.initialized_event = asyncio.Event()
    assert auth.is_initialized() is False
    auth.initialized_event.set()
    assert auth.is_initialized() is True


def test_init_account(auth):
    with mock.patch.object(asyncio, "create_task", mock.Mock(return_value="task")) as create_task_mock, \
            mock.patch.object(auth, "_initialize_account", mock.Mock(return_value="coro")) \
                    as _auth_and_fetch_account_mock:
        auth.init_account(True)
        create_task_mock.assert_called_once_with("coro")
        _auth_and_fetch_account_mock.assert_called_once()
        assert auth._fetch_account_task == "task"


async def test_bot_data_update(auth):
    with (
        mock.patch.object(auth, "is_logged_in_and_has_selected_bot", mock.Mock(return_value=True)) as is_logged_in_and_has_selected_bot_mock,
        mock.patch.object(auth.supabase_client, "refresh_session", mock.AsyncMock()) as refresh_session_mock,
        mock.patch.object(auth, "auto_reauthenticate", mock.AsyncMock(return_value=True)) as auto_reauthenticate_mock,
        mock.patch.object(auth, "logout", mock.AsyncMock()) as logout_mock,
    ):
        @community.authentication._bot_data_update
        async def ok_func(*args, **kwargs):
            # do not raise
            return "result"
        
        await ok_func(auth)
        is_logged_in_and_has_selected_bot_mock.assert_called_once()
        refresh_session_mock.assert_not_called()
        auto_reauthenticate_mock.assert_not_called()
        logout_mock.assert_not_called()
        is_logged_in_and_has_selected_bot_mock.reset_mock()

        @community.authentication._bot_data_update
        async def error_func(*args, **kwargs):
            raise Exception("error")
        await error_func(auth)
        is_logged_in_and_has_selected_bot_mock.assert_called_once()
        refresh_session_mock.assert_not_called()
        auto_reauthenticate_mock.assert_not_called()
        logout_mock.assert_not_called()
        is_logged_in_and_has_selected_bot_mock.reset_mock()

        _calls = []
        @community.authentication._bot_data_update
        async def expired_session_and_retry_error_func(*args, **kwargs):
            if len(_calls) == 0:
                _calls.append(1)
                raise postgrest.exceptions.APIError({'message': 'JWT expired', 'code': 'PGRST303', 'hint': None, 'details': None})
        await expired_session_and_retry_error_func(auth)
        assert is_logged_in_and_has_selected_bot_mock.call_count == 2 # called twice: once for the 1st call, once after the refresh session call
        refresh_session_mock.assert_called_once() # refresh session has been called
        auto_reauthenticate_mock.assert_not_called()
        logout_mock.assert_not_called()
        is_logged_in_and_has_selected_bot_mock.reset_mock()
        refresh_session_mock.reset_mock()

        _calls = []
        @community.authentication._bot_data_update
        async def expired_session_ok_after_reauthenticate_error_func(*args, **kwargs):
            if len(_calls) < 2:
                _calls.append(1)
                raise postgrest.exceptions.APIError({'message': 'JWT expired', 'code': 'PGRST303', 'hint': None, 'details': None})
            return "result"
        await expired_session_ok_after_reauthenticate_error_func(auth)
        assert is_logged_in_and_has_selected_bot_mock.call_count == 3 # called 3 times: once for the 1st call, once after the refresh session call, once after the auto reauthenticate call
        refresh_session_mock.assert_called_once() # refresh session has been called
        auto_reauthenticate_mock.assert_called_once()
        logout_mock.assert_not_called()
        is_logged_in_and_has_selected_bot_mock.reset_mock()
        refresh_session_mock.reset_mock()

        with mock.patch.object(auth, "auto_reauthenticate", mock.AsyncMock(return_value=False)) as auto_reauthenticate_mock:
            @community.authentication._bot_data_update
            async def always_expired_session_error_func(*args, **kwargs):
                raise postgrest.exceptions.APIError({'message': 'JWT expired', 'code': 'PGRST303', 'hint': None, 'details': None})
            await always_expired_session_error_func(auth)
            assert is_logged_in_and_has_selected_bot_mock.call_count == 2 # called 2 times: once for the 1st call, once after the refresh session call
            refresh_session_mock.assert_called_once() # refresh session has been called
            auto_reauthenticate_mock.assert_called_once()
            logout_mock.assert_called_once()
            is_logged_in_and_has_selected_bot_mock.reset_mock()
            refresh_session_mock.reset_mock()


@pytest.mark.asyncio
async def test_stop(auth):
    auth._fetch_account_task = mock.Mock()
    auth._fetch_account_task.cancel = mock.Mock()
    auth._fetch_account_task.done = mock.Mock(return_value=True)
    await auth.stop()
    auth.supabase_client.aclose.assert_awaited_once()
    auth.supabase_client.aclose.reset_mock()
    auth._fetch_account_task.cancel.assert_not_called()
    auth._fetch_account_task.done = mock.Mock(return_value=False)

    await auth.stop()
    auth.supabase_client.aclose.assert_awaited_once()
    auth._fetch_account_task.cancel.assert_called_once()

    auth.supabase_client.aclose.reset_mock()
    auth._fetch_account_task.cancel.reset_mock()
    await auth.stop()
    auth.supabase_client.aclose.assert_awaited_once()
    auth._fetch_account_task.cancel.assert_called_once()


def test_is_node_wallet_configured(auth):
    auth._wallet_backend = mock.Mock()
    auth._wallet_backend.list_wallets.return_value = []
    assert auth.is_node_wallet_configured() is False

    auth._wallet_backend.list_wallets.return_value = [mock.Mock()]
    assert auth.is_node_wallet_configured() is True


class TestGetWalletSyncStorageMasterConfigRead:
    def test_reads_master_config_without_activating_profile(self):
        auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
        master_config = mock.Mock()
        sync_storage = mock.Mock()
        with mock.patch(
            "octobot.community.authentication.user_root_folder_provider.get_sync_data_root",
            mock.Mock(return_value="/master/user"),
        ), mock.patch(
            "octobot.community.authentication.user_root_folder_provider.get_user_root_folder",
            mock.Mock(return_value="/child/automation"),
        ), mock.patch(
            "octobot.community.authentication.os.path.isfile",
            mock.Mock(return_value=True),
        ), mock.patch(
            "octobot.community.authentication.commons_configuration.Configuration",
            mock.Mock(return_value=master_config),
        ) as configuration_cls_mock, mock.patch(
            "octobot.community.authentication.supabase_backend.SyncConfigurationStorage",
            mock.Mock(return_value=sync_storage),
        ) as sync_storage_cls_mock:
            result = auth._get_wallet_sync_storage()
        configuration_cls_mock.assert_called_once()
        master_config.read.assert_called_once_with(should_raise=False, activate_profile=False)
        sync_storage_cls_mock.assert_called_once_with(master_config)
        assert result is sync_storage


class TestClearLocalDataIfNecessary:
    def test_noop_on_cloud_environment(self, auth):
        with mock.patch.object(constants, "IS_CLOUD_ENV", True), mock.patch.object(
            auth, "_clear_bot_scoped_config", mock.Mock()
        ) as clear_mock:
            auth.clear_local_data_if_necessary()
        clear_mock.assert_not_called()

    def test_clears_bot_scoped_data_when_config_path_binding_is_stale(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        config = octobot_commons.configuration.Configuration(
            str(config_path),
            str(tmp_path / "profiles"),
        )
        config.config = {
            constants.CONFIG_COMMUNITY: {
                constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER: "old-identifier",
            }
        }
        with mock.patch.object(
            community.CommunityAuthentication,
            "_create_client",
            return_value=mock.Mock(),
        ):
            auth = community.CommunityAuthentication(config=config, use_as_singleton=False)
        with mock.patch.object(
            octobot_commons.configuration.Configuration, "save", mock.Mock()
        ), mock.patch.object(auth, "_clear_bot_scoped_config", mock.Mock()) as clear_mock:
            auth.clear_local_data_if_necessary()
        clear_mock.assert_called_once()

    def test_keeps_bot_scoped_data_when_config_path_binding_matches(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        import octobot.community.activity_analysis.config_path_binding as config_path_binding
        fingerprint = config_path_binding.fingerprint_config_path(str(config_path))
        config = octobot_commons.configuration.Configuration(
            str(config_path),
            str(tmp_path / "profiles"),
        )
        config.config = {
            constants.CONFIG_COMMUNITY: {
                constants.CONFIG_COMMUNITY_LOCAL_DATA_IDENTIFIER: fingerprint,
            }
        }
        with mock.patch.object(
            community.CommunityAuthentication,
            "_create_client",
            return_value=mock.Mock(),
        ):
            auth = community.CommunityAuthentication(config=config, use_as_singleton=False)
        with mock.patch.object(auth, "_clear_bot_scoped_config", mock.Mock()) as clear_mock:
            auth.clear_local_data_if_necessary()
        clear_mock.assert_not_called()


class TestClearBotScopedConfig:
    def test_clears_activity_bot_id(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}", encoding="utf-8")
        config = octobot_commons.configuration.Configuration(
            str(config_path),
            str(tmp_path / "profiles"),
        )
        config.config = {
            constants.CONFIG_COMMUNITY: {
                constants.CONFIG_COMMUNITY_BOT_ID: "cloud-bot-id",
            },
            octobot_commons.constants.CONFIG_METRICS: {
                octobot_commons.constants.CONFIG_METRICS_ACTIVITY_BOT_ID: "activity-bot-id",
            },
        }
        with mock.patch.object(
            community.CommunityAuthentication,
            "_create_client",
            return_value=mock.Mock(),
        ):
            auth = community.CommunityAuthentication(config=config, use_as_singleton=False)
        with mock.patch.object(auth, "_save_bot_id", mock.Mock()) as save_bot_id_mock, \
                mock.patch.object(auth, "save_tradingview_email", mock.Mock()), \
                mock.patch.object(auth, "_save_mqtt_device_uuid", mock.Mock()), \
                mock.patch.object(auth, "save_tradingview_email_confirmed", mock.Mock()):
            auth._clear_bot_scoped_config()
        save_bot_id_mock.assert_called_once_with("")
        assert (
            config.config[octobot_commons.constants.CONFIG_METRICS][
                octobot_commons.constants.CONFIG_METRICS_ACTIVITY_BOT_ID
            ]
            == ""
        )


class TestFetchPrivateData:
    async def test_process_child_sets_pending_flag_with_install_only(self):
        config = mock.Mock()
        config.uses_shared_reference_tentacles.return_value = True
        config.get_tentacles_setup_config_for_package_operations.return_value = mock.Mock()
        auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
        auth.logger = mock.Mock()
        auth.config = config
        auth.user_account = community_user_account.CommunityUserAccount()
        auth.user_account.community_package_urls = []
        auth.is_logged_in = mock.Mock(return_value=True)
        auth.get_saved_mqtt_device_uuid = mock.Mock(return_value="mqtt-uuid")
        auth._fetch_extensions_details = mock.AsyncMock(
            return_value=(["premium"], ["https://premium.example/pkg.zip"], "mqtt-uuid", "tv@example.com")
        )
        auth.save_installed_package_urls = mock.Mock()
        auth.save_tradingview_email = mock.Mock()
        auth._save_mqtt_device_uuid = mock.Mock()
        auth.has_open_source_package = mock.Mock(return_value=False)
        auth._refresh_products = mock.AsyncMock()
        auth._fetched_private_data = None
        with mock.patch.object(
            constants,
            "DISABLE_COMMUNITY_EXTENSIONS_CHECK",
            False,
        ), mock.patch(
            "octobot.community.tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary",
            new_callable=mock.AsyncMock,
            return_value=True,
        ) as has_tentacles_mock:
            await auth.fetch_private_data()
        has_tentacles_mock.assert_awaited_once_with(auth, install_only=True)
        assert auth.user_account.has_pending_packages_to_install is True

    async def test_sync_profile_fetch_private_data_does_not_use_profile_tentacles_path(self):
        config = mock.Mock()
        config.uses_shared_reference_tentacles.return_value = False
        config.profile = mock.Mock()
        config.profile.is_profile_data_tentacle_backed.return_value = True
        setup_config = mock.Mock()
        config.get_tentacles_setup_config_for_package_operations.return_value = setup_config
        auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
        auth.logger = mock.Mock()
        auth.config = config
        auth.user_account = community_user_account.CommunityUserAccount()
        auth.user_account.community_package_urls = []
        auth.is_logged_in = mock.Mock(return_value=True)
        auth.get_saved_mqtt_device_uuid = mock.Mock(return_value="mqtt-uuid")
        auth._fetch_extensions_details = mock.AsyncMock(
            return_value=(["premium"], ["https://premium.example/pkg.zip"], "mqtt-uuid", "tv@example.com")
        )
        auth.save_installed_package_urls = mock.Mock()
        auth.save_tradingview_email = mock.Mock()
        auth._save_mqtt_device_uuid = mock.Mock()
        auth.has_open_source_package = mock.Mock(return_value=False)
        auth._refresh_products = mock.AsyncMock()
        auth._fetched_private_data = None
        with mock.patch.object(
            constants,
            "DISABLE_COMMUNITY_EXTENSIONS_CHECK",
            False,
        ), mock.patch(
            "octobot.community.tentacles_packages.get_to_install_and_remove_tentacles",
            return_value=([], [], False),
        ):
            await auth.fetch_private_data()
        config.get_tentacles_config_path.assert_not_called()
        config.get_tentacles_setup_config_for_package_operations.assert_called()

    async def test_non_process_child_sets_pending_flag_only(self):
        config = mock.Mock()
        config.uses_shared_reference_tentacles.return_value = False
        auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
        auth.logger = mock.Mock()
        auth.config = config
        auth.user_account = community_user_account.CommunityUserAccount()
        auth.user_account.community_package_urls = []
        auth.is_logged_in = mock.Mock(return_value=True)
        auth.get_saved_mqtt_device_uuid = mock.Mock(return_value="mqtt-uuid")
        auth._fetch_extensions_details = mock.AsyncMock(
            return_value=(["premium"], ["https://premium.example/pkg.zip"], "mqtt-uuid", "tv@example.com")
        )
        auth.save_installed_package_urls = mock.Mock()
        auth.save_tradingview_email = mock.Mock()
        auth._save_mqtt_device_uuid = mock.Mock()
        auth.has_open_source_package = mock.Mock(return_value=False)
        auth._refresh_products = mock.AsyncMock()
        auth._fetched_private_data = None
        with mock.patch.object(
            constants,
            "DISABLE_COMMUNITY_EXTENSIONS_CHECK",
            False,
        ), mock.patch(
            "octobot.community.tentacles_packages.has_tentacles_to_install_and_uninstall_tentacles_if_necessary",
            new_callable=mock.AsyncMock,
            return_value=True,
        ) as has_tentacles_mock:
            await auth.fetch_private_data()
        has_tentacles_mock.assert_awaited_once_with(auth, install_only=False)
        assert auth.user_account.has_pending_packages_to_install is True


def test_sync_server_url_is_a_bare_origin():
    # octobot_sync.client/mirror.writer append SYNC_MOUNT_PATH themselves; a pre-suffixed
    # default here doubles the "/sync" segment and 404s before reaching the sync server.
    assert not constants.SYNC_SERVER_URL.rstrip("/").endswith("/sync")
    assert not constants.STAGING_SYNC_SERVER_URL.rstrip("/").endswith("/sync")


def _new_auth_for_signal_session_tests():
    auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
    auth._dk_sessions = {}
    auth._dk_session_lock = asyncio.Lock()
    return auth


class TestGetSessionForAddress:
    async def test_returns_the_same_session_on_a_second_call_for_the_same_address(self):
        auth = _new_auth_for_signal_session_tests()
        auth.get_wallet = mock.Mock(return_value=mock.Mock(private_key="pk"))
        sentinel_session = mock.Mock()
        with (
            mock.patch.object(
                octobot.community.authentication.identifiers_provider.IdentifiersProvider,
                "SYNC_SERVER_URL",
                _TEST_SYNC_URL,
            ),
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "derived_identity_for_mirror",
                return_value="derived-identity",
            ),
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "build_mirror_session",
                mock.AsyncMock(return_value=sentinel_session),
            ) as mock_build_mirror_session,
        ):
            first = await auth.get_session_for_address("0xabc")
            second = await auth.get_session_for_address("0xabc")

        assert first is sentinel_session
        assert second is sentinel_session
        mock_build_mirror_session.assert_awaited_once()

    async def test_raises_wallet_error_when_sync_server_url_is_not_configured(self):
        auth = _new_auth_for_signal_session_tests()
        with mock.patch.object(
            octobot.community.authentication.identifiers_provider.IdentifiersProvider,
            "SYNC_SERVER_URL",
            "",
        ):
            with pytest.raises(octobot.community.wallet_backend.WalletError):
                await auth.get_session_for_address("0xabc")

    async def test_builds_the_session_with_the_bare_sync_url_and_signal_name(self):
        auth = _new_auth_for_signal_session_tests()
        auth.get_wallet = mock.Mock(return_value=mock.Mock(private_key="pk"))
        with (
            mock.patch.object(
                octobot.community.authentication.identifiers_provider.IdentifiersProvider,
                "SYNC_SERVER_URL",
                _TEST_SYNC_URL,
            ),
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "derived_identity_for_mirror",
                return_value="derived-identity",
            ) as mock_derive,
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "build_mirror_session",
                mock.AsyncMock(return_value=mock.Mock()),
            ) as mock_build_mirror_session,
        ):
            await auth.get_session_for_address("0xabc")

        mock_derive.assert_called_once_with("pk")
        mock_build_mirror_session.assert_awaited_once_with(
            "derived-identity", _TEST_SYNC_URL, name="octobot-signals"
        )

    async def test_distinct_addresses_get_distinct_sessions(self):
        auth = _new_auth_for_signal_session_tests()
        auth.get_wallet = mock.Mock(return_value=mock.Mock(private_key="pk"))
        sessions = [mock.Mock(), mock.Mock()]
        with (
            mock.patch.object(
                octobot.community.authentication.identifiers_provider.IdentifiersProvider,
                "SYNC_SERVER_URL",
                _TEST_SYNC_URL,
            ),
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "derived_identity_for_mirror",
                return_value="derived-identity",
            ),
            mock.patch.object(
                octobot.community.authentication.sync_session_writer,
                "build_mirror_session",
                mock.AsyncMock(side_effect=sessions),
            ),
        ):
            first = await auth.get_session_for_address("0xabc")
            second = await auth.get_session_for_address("0xdef")

        assert first is sessions[0]
        assert second is sessions[1]
        assert first is not second


class TestStopClosesCachedDkSessions:
    async def test_stop_closes_and_clears_cached_dk_sessions(self):
        auth = community.CommunityAuthentication.__new__(community.CommunityAuthentication)
        auth.logger = mock.Mock()
        auth._fetch_account_task = None
        auth.supabase_client = mock.Mock(aclose=mock.AsyncMock())
        auth._community_feed = None
        auth.community_bot = None
        auth._sync_client = None
        cached_session = mock.Mock(
            content_client=mock.Mock(close=mock.AsyncMock()),
            account_client=mock.Mock(close=mock.AsyncMock()),
        )
        auth._dk_sessions = {"0xabc": cached_session}

        await auth.stop()

        cached_session.content_client.close.assert_awaited_once()
        cached_session.account_client.close.assert_awaited_once()
        assert auth._dk_sessions == {}

