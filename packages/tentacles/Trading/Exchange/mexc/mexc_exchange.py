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
import contextlib
import decimal
import time
import typing
import ccxt
import hashlib

import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.enums as trading_enums
import octobot_trading.errors
import octobot_commons.symbols as symbols_util
import octobot_commons.constants as commons_constants
import octobot_commons
import octobot_trading.constants as constants


class MEXCConnector(exchanges.CCXTConnector):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_signed_requests: typing.Optional[bool] = None

    def _create_client(self, force_unauth=False):
        super()._create_client(force_unauth=force_unauth)
        self.client.sign = self._lazy_maybe_force_signed_requests(self.client.sign)

    def _lazy_maybe_force_signed_requests(self, origin_ccxt_sign):
        def lazy_sign(path, api, method, params, headers, body):
            if self._force_signed_requests is None:
                self._force_signed_requests = self.exchange_manager.exchange.requires_authentication(
                    self.exchange_manager.exchange.tentacle_config,
                    None,
                    None,
                    self.exchange_manager,
                )
                if self._force_signed_requests:
                    self.logger.info(f"Enabled force signing requests for {self.exchange_manager.exchange_name}")
            ccxt_sign_result = origin_ccxt_sign(path, api, method, params, headers, body)
            if self._force_signed_requests:
                url = ccxt_sign_result.get("url") or ""
                ccxt_headers = ccxt_sign_result.get("headers") or {}
                if "signature=" in url or "Signature" in ccxt_headers:
                    # already signed
                    return ccxt_sign_result
                # force signature
                return self._force_sign(path, api, method, params, headers, body)
            return ccxt_sign_result
        return lazy_sign

    # TODO potentially later: replace by ob_mexc sign when ob_websocket are supported
    def _force_sign(self, path, api, method, params, headers, body):
        self = self.client  # to use the same code as ccxt.async_support.mexc.sign (same self)
        # same code as ccxt.async_support.mexc.sign but forced to sign
        section = self.safe_string(api, 0)
        access = self.safe_string(api, 1)
        path, params = self.resolve_path(path, params)
        url = None
        if section == 'spot' or section == 'broker':
            if section == 'broker':
                url = self.urls['api'][section][access] + '/' + path
            else:
                url = self.urls['api'][section][access] + '/api/' + self.version + '/' + path
            urlParams = params
            if True or access == 'private':  # local override to force signature
                if section == 'broker' and ((method == 'POST') or (method == 'PUT') or (method == 'DELETE')):
                    urlParams = {
                        'timestamp': self.nonce(),
                        'recvWindow': self.safe_integer(self.options, 'recvWindow', 5000),
                    }
                    body = self.json(params)
                else:
                    urlParams['timestamp'] = self.nonce()
                    urlParams['recvWindow'] = self.safe_integer(self.options, 'recvWindow', 5000)
            paramsEncoded = ''
            if urlParams:
                paramsEncoded = self.urlencode(urlParams)
                url += '?' + paramsEncoded
            if True or access == 'private':  # local override to force signature
                self.check_required_credentials()
                signature = self.hmac(self.encode(paramsEncoded), self.encode(self.secret), hashlib.sha256)
                url += '&' + 'signature=' + signature
                headers = {
                    'X-MEXC-APIKEY': self.apiKey,
                    'source': self.safe_string(self.options, 'broker', 'CCXT'),
                }
            if (method == 'POST') or (method == 'PUT') or (method == 'DELETE'):
                headers['Content-Type'] = 'application/json'
        elif section == 'contract' or section == 'spot2':
            url = self.urls['api'][section][access] + '/' + self.implode_params(path, params)
            params = self.omit(params, self.extract_params(path))
            if False and access == 'public':  # local override to force signature
                if params:
                    url += '?' + self.urlencode(params)
            else:
                self.check_required_credentials()
                timestamp = str(self.nonce())
                auth = ''
                headers = {
                    'ApiKey': self.apiKey,
                    'Request-Time': timestamp,
                    'Content-Type': 'application/json',
                    'source': self.safe_string(self.options, 'broker', 'CCXT'),
                }
                if method == 'POST':
                    auth = self.json(params)
                    body = auth
                else:
                    params = self.keysort(params)
                    if params:
                        auth += self.urlencode(params)
                        url += '?' + auth
                auth = self.apiKey + timestamp + auth
                signature = self.hmac(self.encode(auth), self.encode(self.secret), hashlib.sha256)
                headers['Signature'] = signature
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

class MEXC(exchanges.RestExchange):
    DEFAULT_CONNECTOR_CLASS = MEXCConnector
    @classmethod
    def get_name(cls):
        return 'mexc'

    # # now useless? see if needed in the future
    # async def get_all_tradable_symbols(self, active_only=True) -> set[str]:
    #     """
    #     Override if the exchange is not allowing trading for all available symbols (ex: MEXC)
    #     :return: the list of all symbols supported by the exchange that can currently be traded through API
    #     """
    #     if CACHED_MEXC_API_HANDLED_SYMBOLS.should_be_updated():
    #         await CACHED_MEXC_API_HANDLED_SYMBOLS.update(self)
    #     return CACHED_MEXC_API_HANDLED_SYMBOLS.symbols


# class APIHandledSymbols:
#     """
#     MEXC has pairs that are sometimes tradable from the exchange UI but not from the API. Get the list of
#     currently api tradable symbols from the defaultSymbols endpoint.
#     """

#     def __init__(self, update_interval):
#         self.symbols = set()
#         self.last_update = 0
#         self._update_interval = update_interval

#     def should_be_updated(self):
#         return time.time() - self._update_interval >= self._update_interval

#     async def update(self, exchange):
#         try:
#             result = await exchange.connector.client.spot2_public_get_market_api_default_symbols()
#             self.symbols = set(
#                 # in some cases, "_" is not replaced as symbol is not found in markets
#                 exchange.connector.client.safe_market(s)["symbol"].replace("_", octobot_commons.MARKET_SEPARATOR)
#                 for s in result["data"]["symbol"]
#             )
#             self.last_update = time.time()
#             exchange.logger.info(f"Updated handled symbols, list: {self.symbols}")
#         except Exception as err:
#             exchange.logger.exception(err, True, f"Error when fetching api-tradable symbols: {err}")

# # make it available a singleton
# CACHED_MEXC_API_HANDLED_SYMBOLS = APIHandledSymbols(commons_constants.DAYS_TO_SECONDS)
