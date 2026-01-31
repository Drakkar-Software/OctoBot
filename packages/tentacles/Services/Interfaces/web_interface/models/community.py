#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import typing

import octobot_services.interfaces.util as interfaces_util
import octobot.community as octobot_community
import octobot.commands as octobot_commands
import octobot.constants as octobot_constants
import octobot_commons.authentication as authentication
import octobot_trading.api as trading_api


def get_community_metrics_to_display():
    return interfaces_util.run_in_bot_async_executor(octobot_community.get_community_metrics())


def can_get_community_metrics():
    return octobot_community.can_read_metrics(interfaces_util.get_edited_config(dict_only=False))


def get_owned_packages() -> list[str]:
    authenticator = authentication.Authenticator.instance()
    return authenticator.get_owned_packages()


def has_owned_packages_to_install() -> list[str]:
    authenticator = authentication.Authenticator.instance()
    return authenticator.has_owned_packages_to_install()


def update_owned_packages():
    authenticator = authentication.Authenticator.instance()
    interfaces_util.run_in_bot_main_loop(authenticator.fetch_private_data(reset=True))


def has_open_source_package() -> bool:
    authenticator = authentication.Authenticator.instance()
    return authenticator.has_open_source_package()


def get_checkout_url(payment_method, redirect_url) -> (bool, str):
    selected_payment_method = "crypto" if payment_method == "crypto" else "credit_card"
    authenticator = authentication.Authenticator.instance()
    try:
        url = interfaces_util.run_in_bot_main_loop(authenticator.fetch_checkout_url(selected_payment_method, redirect_url))
        return True, url
    except BaseException:
        return False, "error when fetching checkout url"


def get_tradingview_email_address() -> str:
    return authentication.Authenticator.instance().get_saved_tradingview_email()


def get_last_email_address_confirm_code_email_content() -> typing.Optional[str]:
    return authentication.Authenticator.instance().get_last_email_address_confirm_code_email_content()


def wait_for_email_address_confirm_code_email():
    return interfaces_util.run_in_bot_main_loop(
        authentication.Authenticator.instance().trigger_wait_for_email_address_confirm_code_email()
    )


def get_cloud_strategies(authenticator) -> list[octobot_community.StrategyData]:
    return interfaces_util.run_in_bot_main_loop(authenticator.get_strategies())


def get_cloud_strategy(authenticator, strategy_id: str) -> octobot_community.StrategyData:
    return interfaces_util.run_in_bot_main_loop(authenticator.get_strategy(strategy_id))


def get_preview_tentacles_packages(url_for):
    c1 = octobot_community.CommunityTentaclesPackage(
        "AI candles analyser",
        "Tentacles packages offering artificial intelligence analysis tools based on candles shapes.",
        None, True,
        [url_for("static", filename="img/community/tentacles_packages_previews/octobot.png")], None, None, None)
    c1.uninstalled = False
    c2 = octobot_community.CommunityTentaclesPackage(
        "Telegram portfolio management",
        "Manage your portfolio directly from the telegram interface.",
        None, False,
        [url_for("static", filename="img/community/tentacles_packages_previews/telegram.png")], None, None, None)
    c2.uninstalled = False
    c3 = octobot_community.CommunityTentaclesPackage(
        "Mobile first web interface",
        "Use a mobile oriented interface for your OctoBot.",
        None, True,
        [url_for("static", filename="img/community/tentacles_packages_previews/mobile.png")], None, None, None)
    c3.uninstalled = True
    return [c1, c2, c3]


def get_current_octobots_stats():
    return interfaces_util.run_in_bot_async_executor(octobot_community.get_current_octobots_stats())


def _format_bot(bot):
    return {
        "name": octobot_community.CommunityUserAccount.get_bot_name_or_id(bot) if bot else None,
        "id": octobot_community.CommunityUserAccount.get_bot_id(bot) if bot else None,
    }


def get_all_user_bots():
    # reload user bots to make sure the list is up to date
    interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().load_user_bots())
    return sorted([
        _format_bot(bot)
        for bot in authentication.Authenticator.instance().user_account.get_all_user_bots_raw_data()
    ], key=lambda d: d["name"])


def get_selected_user_bot():
    return _format_bot(authentication.Authenticator.instance().user_account.get_selected_bot_raw_data())


def select_bot(bot_id):
    interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().select_bot(bot_id))


def create_new_bot():
    return interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().create_new_bot())


def can_select_bot():
    return not octobot_constants.COMMUNITY_BOT_ID


def can_logout():
    return not authentication.Authenticator.instance().must_be_authenticated_through_authenticator()


def get_user_account_id():
    return authentication.Authenticator.instance().get_user_id()


def has_filled_form(form_id):
    return authentication.Authenticator.instance().has_filled_form(form_id)


def register_user_submitted_form(user_id, form_id):
    try:
        if get_user_account_id() != user_id:
            return False, "Invalid user id"
        interfaces_util.run_in_bot_main_loop(
            authentication.Authenticator.instance().register_filled_form(form_id)
        )
    except Exception as e:
        return False, f"Error when registering filled form {e}"
    return True, "Thank you for your feedback !"


def get_followed_strategy_url():
    trading_mode = interfaces_util.get_bot_api().get_trading_mode()
    if trading_mode is None:
        return None
    identifier = trading_api.get_trading_mode_followed_strategy_signals_identifier(trading_mode)
    if identifier is None:
        return None
    return authentication.Authenticator.instance().get_signal_community_url(
        identifier
    )


def is_community_feed_connected():
    return authentication.Authenticator.instance().is_feed_connected()


def get_last_signal_time():
    return authentication.Authenticator.instance().get_feed_last_message_time()


async def _sync_community_account():
    profile_urls = await authentication.Authenticator.instance().get_subscribed_profile_urls()
    return octobot_commands.download_missing_profiles(interfaces_util.get_edited_config(dict_only=False), profile_urls)


def sync_community_account():
    return interfaces_util.run_in_bot_main_loop(_sync_community_account())


def wait_for_login_if_processing():
    try:
        interfaces_util.run_in_bot_main_loop(authentication.Authenticator.instance().wait_for_login_if_processing())
    except asyncio.TimeoutError:
        pass
