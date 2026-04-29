#  Drakkar-Software OctoBot-Tentacles
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
import hashlib
import uuid

import octobot_commons.authentication as authentication
import octobot_services.constants as services_constants
import octobot_services.enums as services_enums
import octobot_services.services as services
import octobot.constants as constants


class TradingViewService(services.AbstractService):
    def __init__(self):
        super().__init__()
        self.requires_token = None
        self.token = None
        self.use_email_alert = None
        self._webhook_url = None

    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def has_required_configuration(self):
        return True

    def get_required_config(self):
        return [
            services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN,
            services_constants.CONFIG_TRADING_VIEW_TOKEN,
            # disabled until TradingView email alerts are restored
            # services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS
        ]

    def get_fields_description(self):
        return {
            services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN: "When enabled the TradingView webhook will require your "
                                                                  "tradingview.com token to process any signal.",
            services_constants.CONFIG_TRADING_VIEW_TOKEN: "Your personal unique tradingview.com token. Can be used to ensure only your "
                                                          "TradingView signals are triggering your OctoBot in case someone else get "
                                                          "your webhook link. You can change it at any moment but remember to change it "
                                                          "on your tradingview.com signal account as well.",
            services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS: (
                f"When enabled, your OctoBot will trade using the free TradingView email alerts. When disabled, "
                f"a webhook configuration is required to trade using TradingView alerts. Requires the "
                f"{constants.OCTOBOT_EXTENSION_PACKAGE_1_NAME}."
            ),
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN: False,
            services_constants.CONFIG_TRADING_VIEW_TOKEN: self.get_security_token(uuid.uuid4().hex),
            # disabled until TradingView email alerts are restored
            # services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS: False,
        }

    def is_improved_by_extensions(self) -> bool:
        return True

    def get_read_only_info(self) -> list[services.ReadOnlyInfo]:
        read_only_info = []
        auth = authentication.Authenticator.instance()
        if auth.is_tradingview_email_confirmed() and (email_address := auth.get_saved_tradingview_email()):
            read_only_info.append(services.ReadOnlyInfo(
                'Email address:', email_address, services_enums.ReadOnlyInfoType.COPYABLE,
                configuration_title="Configure on TradingView", configuration_path="tradingview_email_config"
            ))
        else:
            pass
            # disabled until TradingView email alerts are restored
            # read_only_info.append(services.ReadOnlyInfo(
            #     'Email address:', "Generate email", services_enums.ReadOnlyInfoType.CTA,
            #     path="tradingview_email_config"
            # ))
        if self._webhook_url:
            read_only_info.append(services.ReadOnlyInfo(
                'Webhook url:',
                self._webhook_url,
                services_enums.ReadOnlyInfoType.READONLY
                if self._webhook_url == services_constants.TRADING_VIEW_USING_EMAIL_INSTEAD_OF_WEBHOOK
                else services_enums.ReadOnlyInfoType.COPYABLE,
            ))
        return read_only_info

    @classmethod
    def get_help_page(cls) -> str:
        return f"{constants.OCTOBOT_DOCS_URL}/octobot-interfaces/tradingview"

    def get_endpoint(self) -> None:
        return None

    def get_type(self) -> None:
        return services_constants.CONFIG_TRADING_VIEW

    def get_website_url(self):
        return "https://www.tradingview.com/?aff_id=27595"

    def get_logo(self):
        return "https://in.tradingview.com/static/images/favicon.ico"

    async def prepare(self) -> None:
        try:
            self.requires_token = \
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TRADING_VIEW][
                    services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN]
            self.token = \
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TRADING_VIEW][
                    services_constants.CONFIG_TRADING_VIEW_TOKEN]
            self.use_email_alert = \
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TRADING_VIEW].get(
                    services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS, False
                )
        except KeyError:
            if self.requires_token is None:
                self.requires_token = self.get_default_value()[services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN]
            if self.token is None:
                self.token = self.get_default_value()[services_constants.CONFIG_TRADING_VIEW_TOKEN]
            if self.use_email_alert is None:
                self.use_email_alert = self.get_default_value().get(services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS, False)
            # save new values into config file
            updated_config = {
                services_constants.CONFIG_REQUIRE_TRADING_VIEW_TOKEN: self.requires_token,
                services_constants.CONFIG_TRADING_VIEW_TOKEN: self.token,
            }
            if self.use_email_alert:
                # only save CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS if use_email_alert is True
                # (to keep the option of users still using it)
                updated_config[services_constants.CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS] = self.use_email_alert
            self.save_service_config(services_constants.CONFIG_TRADING_VIEW, updated_config)

    @staticmethod
    def get_security_token(pin_code):
        """
        Generate unique token from pin.  This adds a marginal amount of security.
        :param pin_code: the pin code to use
        :return: the generated token
        """
        token = hashlib.sha224(pin_code.encode('utf-8'))
        return token.hexdigest()

    def register_webhook_url(self, webhook_url):
        self._webhook_url = webhook_url

    def get_successful_startup_message(self):
        return "", True
