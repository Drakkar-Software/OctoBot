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
import octobot.constants as constants
import octobot_commons.authentication as authentication
import octobot_commons.configuration
import octobot_commons.profiles.profile_data

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

AUTH_URL = "https://oh.fake/auth"
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
            started_at=1723659202.0, # not nested config: use bot created_at (2024-08-14T22:13:22.1111+04:00)
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
            started_at=1723644802.0, # not nested config: use bot created_at (2024-08-14T22:13:22.1111+08:00)
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
