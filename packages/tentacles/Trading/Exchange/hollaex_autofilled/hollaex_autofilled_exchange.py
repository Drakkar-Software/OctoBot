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
import cachetools
import aiohttp
import typing
import asyncio
import requests.utils

import octobot_commons.logging as commons_logging
import octobot_commons.constants
import octobot_commons.html_util as html_util
import octobot_trading.exchanges as exchanges
import octobot_trading.errors as errors
import octobot_tentacles_manager.api
from ..hollaex.hollaex_exchange import hollaex


_EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL: dict[str, dict] = {}
# refresh exchange config every day but don't delete outdated info, only replace it with updated ones
_REFRESHED_EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL : cachetools.TTLCache[str, bool] = cachetools.TTLCache(
    maxsize=50, ttl=octobot_commons.constants.DAYS_TO_SECONDS
)

class HollaexAutofilled(hollaex):
    HAS_FETCHED_DETAILS = True

    URL_KEY = "url"
    AUTO_FILLED_KEY = "auto_filled"
    WEBSOCKETS_KEY = "websockets"
    KIT_PATH = "/kit"
    V2_KIT_PATH = f"v2{KIT_PATH}"
    MAX_RATE_LIMIT_ATTEMPTS = 60    # fetch over 3 minutes, every 3s (we can't start the bot if the kit request fails)
    RATE_LIMIT_SLEEP_TIME = 3

    @classmethod
    def supported_autofill_exchanges(cls, tentacle_config):
        return list(tentacle_config[cls.AUTO_FILLED_KEY]) if tentacle_config else []

    @classmethod
    def init_user_inputs_from_class(cls, inputs: dict) -> None:
        pass

    @classmethod
    async def get_autofilled_exchange_details(cls, aiohttp_session, tentacle_config, exchange_name):
        kit_details = await aiohttp_session.get(HollaexAutofilled._get_kit_url(tentacle_config, exchange_name))
        return HollaexAutofilled._parse_autofilled_exchange_details(
            tentacle_config, await kit_details.json(), exchange_name
        )

    def _apply_fetched_details(self, config, exchange_manager):
        self._apply_config(self.get_exchange_details(self.tentacle_config, exchange_manager.exchange_name))

    @classmethod
    async def fetch_exchange_config(
        cls, exchange_config_by_exchange: typing.Optional[dict[str, dict]], exchange_manager
    ):
        hollaex_based_exchange_identifier = cls.get_name()
        if not exchange_config_by_exchange:
            # no override, try using exchange_manager.tentacles_setup_config
            exchange_config_by_exchange = {
                hollaex_based_exchange_identifier: (
                    octobot_tentacles_manager.api.get_tentacle_config(exchange_manager.tentacles_setup_config, cls)
                )
            }
        if not exchange_config_by_exchange or hollaex_based_exchange_identifier not in exchange_config_by_exchange:
            raise KeyError(
                f"{hollaex_based_exchange_identifier} has to be in exchange_config_by_exchange. "
                f"{exchange_config_by_exchange=}"
            )
        tentacle_config = exchange_config_by_exchange[hollaex_based_exchange_identifier]
        await cls._cached_fetch_autofilled_config(tentacle_config, exchange_manager.exchange_name)

    @classmethod
    def _get_user_agent(cls):
        return requests.utils.default_user_agent()

    @classmethod
    def _get_headers(cls):
        return {
            # same as CCXT
            'User-Agent': cls._get_user_agent(),
            "Accept-Encoding": "gzip, deflate"
        }

    @classmethod
    async def _cached_fetch_autofilled_config(cls, tentacle_config, exchange_name) -> dict:
        try:
            exchange_kit_url = cls._get_kit_url(tentacle_config, exchange_name)
        except KeyError:
            raise errors.NotSupported(f"{exchange_name} is not supported by {cls.get_name()}")
        if exchange_kit_url in _REFRESHED_EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL:
            return _EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL[exchange_kit_url]
        commons_logging.get_logger(cls.get_name()).info(
            f"Fetching {exchange_name} HollaEx kit from {exchange_kit_url}"
        )
        async with aiohttp.ClientSession(headers=cls._get_headers()) as session:
            _EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL[exchange_kit_url] = await cls._retry_fetch_when_rate_limit(
                session, exchange_kit_url
            )
            _REFRESHED_EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL[exchange_kit_url] = True
        return _EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL[exchange_kit_url]

    @classmethod
    async def _retry_fetch_when_rate_limit(cls, session, url):
        try:
            for attempt in range(cls.MAX_RATE_LIMIT_ATTEMPTS):
                async with session.get(url) as response:
                    if response.status < 300:
                        return await response.json()
                    elif response.status in (403, 429) or "has banned your IP address" in (await response.text()):
                        # rate limit: sleep and retry
                        commons_logging.get_logger(cls.get_name()).warning(
                            f"Error when fetching {url}: {response.status}. Retrying in {cls.RATE_LIMIT_SLEEP_TIME} seconds"
                        )
                        await asyncio.sleep(cls.RATE_LIMIT_SLEEP_TIME)
                    else:
                        # unexpected error
                        response.raise_for_status()

            commons_logging.get_logger(cls.get_name()).error(
                f"Error when fetching {url}: {response.status}. Max attempts ({cls.MAX_RATE_LIMIT_ATTEMPTS}) reached. "
                f"Error text: {await response.text()}"
            )
            response.raise_for_status()
        except aiohttp.ClientResponseError as err:
            if err.status == 404:
                raise errors.FailedRequest(f"{url} returned 404: not found: {err.message}") from err
            raise # forward unexpected errors
        except aiohttp.ClientConnectionError as err:
            raise errors.NetworkError(
                f"Failed to execute request: {err.__class__.__name__}: {html_util.get_html_summary_if_relevant(err)}"
            ) from err

    def _supports_autofill(self, exchange_name):
        try:
            self._get_kit_url(self.tentacle_config, exchange_name)
            return True
        except KeyError:
            return False

    @classmethod
    def _get_kit_url(cls, tentacle_config, exchange_name) -> str:
        exchange_kit_url = HollaexAutofilled._get_autofilled_config(tentacle_config, exchange_name)[cls.URL_KEY]
        if not exchange_kit_url.endswith(cls.KIT_PATH) and not exchange_kit_url.endswith("/"):
            exchange_kit_url = f"{exchange_kit_url}/"
        if not exchange_kit_url.endswith(cls.KIT_PATH):
            exchange_kit_url = f"{exchange_kit_url}{cls.V2_KIT_PATH}"
        return exchange_kit_url

    @classmethod
    def _has_websocket(cls, tentacle_config, exchange_name):
        return HollaexAutofilled._get_autofilled_config(tentacle_config, exchange_name).get(cls.WEBSOCKETS_KEY, False)

    @classmethod
    def _get_autofilled_config(cls, tentacle_config, exchange_name):
        return tentacle_config[cls.AUTO_FILLED_KEY][exchange_name]

    @classmethod
    def get_exchange_details(cls, tentacle_config, exchange_name) -> typing.Optional[exchanges.ExchangeDetails]:
        return cls._parse_autofilled_exchange_details(
            tentacle_config,
            _EXCHANGE_REMOTE_CONFIG_BY_EXCHANGE_KIT_URL[
                cls._get_kit_url(tentacle_config, exchange_name)
            ],
            exchange_name
        )

    @classmethod
    def _parse_autofilled_exchange_details(cls, tentacle_config, kit_details, exchange_name):
        """
        use /kit to fill in exchange details
        format:
        {
            "api_name": "BitcoinRD Exchange",
            "black_list_countries": [],
            "captcha": {},
            "color": {
                "Black": {
                    "base_background": "#000000",
                    ...
                }
            },
            "defaults": {
                "country": "DO",
                "language": "es",
                "theme": "dark"
            },
            "description": "Primer Exchange 100% Dominicano.",
            "dust": {
                "maker_id": 1,
                "quote": "xht",
                "spread": 0
            },
            "email_verification_required": true,
            "features": {
                "chat": false,
                ...
            },
            "icons": {
                "dark": {
                    "DOP_ICON": "https://bitholla.s3.ap-northeast-2.amazonaws.com/exchange/bitcoinrdexchange/DOP_ICON__dark___1631209668172.png",
                    ...
                },
                "white": {
                    "EXCHANGE_FAV_ICON": "https://bitholla.s3.ap-northeast-2.amazonaws.com/exchange/bitcoinrdexchange/EXCHANGE_FAV_ICON__white___1615349464540.png",
                    ...
                }
            },
            "info": {
                "active": true,
                "collateral_level": "member",
                "created_at": "2021-03-09T14:12:49.012Z",
                "exchange_id": 1512,
                "expiry": "2023-08-27T23:59:59.000Z",
                "initialized": true,
                "is_trial": false,
                "name": "bitcoinrdexchange",
                "period": "year",
                "plan": "fiat",
                "status": true,
                "type": "Cloud",
                "url": "https://api.bitcoinrd.do",
                "user_id": 3536
            },
            "injected_html": {
                "body": "",
                "head": ""
            },
            "injected_values": [],
            "interface": {},
            "links": {
                "api": "https://api.bitcoinrd.do",
                "contact": "",
                "facebook": "",
                "github": "",
                "helpdesk": "mailto:soporte@bitcoinrd.do",
                "information": "",
                "instagram": "",
                "linkedin": "",
                "privacy": "https://bitcoinrd.online/privacy-policy/",
                "referral_label": "Powered by BitcoinRD",
                "referral_link": "https://bitcoinrd.online/",
                "section_1": {
                    "content": {
                        "instagram": "https://www.instagram.com/bitcoinrd/"
                    },
                    "header": {
                        "column_header_1": "RRSS"
                    }
                },
                "section_2": "",
                "telegram": "",
                "terms": "https://bitcoinrd.online/terms/",
                "twitter": "",
                "website": "",
                "whitepaper": ""
            },
            "logo_image": "https://bitholla.s3.ap-northeast-2.amazonaws.com/exchange/bitcoinrdexchange/EXCHANGE_LOGO__dark___1615345052424.png",
            "meta": {
                "default_digital_assets_sort": "change",
                ...
                },
                "versions": {
                    "color": "color-1681492596812",
                    ...
                }
            },
            "native_currency": "usdt",
            "new_user_is_activated": true,
            "offramp": {...},
            "onramp": {...},
            "setup_completed": true,
            "strings": {
                "en": { ...}
            },
            "title": "",
            "user_meta": {},
            "user_payments": {},
            "valid_languages": "en,es,fr"
        }
        """
        return exchanges.ExchangeDetails(
            exchange_name,
            kit_details.get("api_name", exchange_name),
            kit_details["links"].get("referral_link", ""),
            kit_details["info"]["url"], # required (API url)
            kit_details.get("logo_image", ""),
            HollaexAutofilled._has_websocket(
                tentacle_config,
                exchange_name
            )
        )

    def _apply_config(self, autofilled_exchange_details: exchanges.ExchangeDetails):
        self.logger = commons_logging.get_logger(autofilled_exchange_details.name)
        self.tentacle_config[self.REST_KEY] = autofilled_exchange_details.api
        self.tentacle_config[self.HAS_WEBSOCKETS_KEY] = autofilled_exchange_details.has_websocket

    @classmethod
    def is_supporting_sandbox(cls) -> bool:
        return False

    @classmethod
    def get_rest_name(cls, exchange_manager):
        return hollaex.get_name()

    def get_associated_websocket_exchange_name(self):
        return self.get_name()

    @classmethod
    def get_name(cls):
        return cls.__name__
