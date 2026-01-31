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
import typing
import hashlib
import ccxt

import octobot_trading.exchanges as exchanges
import octobot_trading.constants as constants
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants


class LBankSignConnectorMixin:
    def __init__(self):
        # used by default to force signed requests
        self._force_signed_requests: typing.Optional[bool] = None

    def _lazy_maybe_force_signed_requests(self, origin_ccxt_sign):
        def lazy_sign(path, api, method, params, headers, body):
            if self._force_signed_requests is None:
                # force sign if the exchange requires authentication or if the connector is authenticated
                self._force_signed_requests = self.exchange_manager.exchange.requires_authentication(
                    self.exchange_manager.exchange.tentacle_config, None, None
                ) or (
                    self.exchange_manager.exchange.connector 
                    and self.exchange_manager.exchange.connector.is_authenticated
                )
                if self._force_signed_requests:
                    self.logger.info(f"Enabled force signing requests for {self.exchange_manager.exchange_name}")
            ccxt_sign_result = origin_ccxt_sign(path, api, method, params, headers, body)
            if self._force_signed_requests:
                if self.exchange_manager.exchange.is_authenticated_request(
                    ccxt_sign_result.get("url"), ccxt_sign_result.get("method"), 
                    ccxt_sign_result.get("headers"), ccxt_sign_result.get("body")
                ):
                    # already signed
                    return ccxt_sign_result
                # force signature
                return self._force_sign(path, api, method, params, headers, body)
            return ccxt_sign_result
        return lazy_sign

    def _force_sign(self, path, api, method, params, headers, body):
        self = self.client  # to use the same code as ccxt.async_support.lbank.sign (same self)
        # same code as ccxt.async_support.lbank.sign but forced to sign
        query = self.omit(params, self.extract_params(path))
        url = self.urls['api']['rest'] + '/' + self.version + '/' + self.implode_params(path, params)
        # Every spot endpoint ends with ".do"
        if api[0] == 'spot':
            url += '.do'
        else:
            url = self.urls['api']['contract'] + '/' + self.implode_params(path, params)
        # local override
        # if api[1] == 'public':
        #     if query:
        #         url += '?' + self.urlencode(self.keysort(query))
        # else:
        # end local override
        self.check_required_credentials()
        timestamp = str(self.milliseconds())
        echostr = self.uuid22() + self.uuid16()
        query = self.extend({
            'api_key': self.apiKey,
        }, query)
        signatureMethod = None
        if len(self.secret) > 32:
            signatureMethod = 'RSA'
        else:
            signatureMethod = 'HmacSHA256'
        auth = self.rawencode(self.keysort(self.extend({
            'echostr': echostr,
            'signature_method': signatureMethod,
            'timestamp': timestamp,
        }, query)))
        encoded = self.encode(auth)
        hash = self.hash(encoded, 'md5')
        uppercaseHash = hash.upper()
        sign = None
        if signatureMethod == 'RSA':
            cacheSecretAsPem = self.safe_bool(self.options, 'cacheSecretAsPem', True)
            pem = None
            if cacheSecretAsPem:
                pem = self.safe_value(self.options, 'pem')
                if pem is None:
                    pem = self.convert_secret_to_pem(self.encode(self.secret))
                    self.options['pem'] = pem
            else:
                pem = self.convert_secret_to_pem(self.encode(self.secret))
            sign = self.rsa(uppercaseHash, pem, 'sha256')
        elif signatureMethod == 'HmacSHA256':
            sign = self.hmac(self.encode(uppercaseHash), self.encode(self.secret), hashlib.sha256)
        query['sign'] = sign
        # local override
        all_params = self.urlencode(self.keysort(query))
        if api[1] == 'public':
            if query:
                url += '?' + all_params
        else:
            body = all_params
        # end local override
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'timestamp': timestamp,
            'signature_method': signatureMethod,
            'echostr': echostr,
        }
        return {'url': url, 'method': method, 'body': body, 'headers': headers}


class LBankConnector(exchanges.CCXTConnector, LBankSignConnectorMixin):

    def __init__(self, *args, **kwargs):
        exchanges.CCXTConnector.__init__(self, *args, **kwargs)
        LBankSignConnectorMixin.__init__(self)
        # used by default to force signed requests
        self._force_signed_requests: typing.Optional[bool] = None

    def _create_client(self, force_unauth=False):
        exchanges.CCXTConnector._create_client(self, force_unauth=force_unauth)
        self.register_client_mocks()

    def register_client_mocks(self):
        self.client.sign = self._lazy_maybe_force_signed_requests(self.client.sign)
        self.client.parse_order = self.parse_order_mock(self.client)
    
    def parse_order_mock(self, client):
        origin_parse_order = client.parse_order
        def _mocked_parse_order(order, market=None):
            try:
                return origin_parse_order(order, market)
            except AttributeError as err:
                if "'NoneType' object has no attribute 'split'" in str(err):
                    # no order fetched
                    raise ccxt.OrderNotFound(f"Order not found")
                # should not happen
                raise
        return _mocked_parse_order


class LBank(exchanges.RestExchange):
    DEFAULT_CONNECTOR_CLASS = LBankConnector
    FIX_MARKET_STATUS = True
    REMOVE_MARKET_STATUS_PRICE_LIMITS = True
    SUPPORT_FETCHING_CANCELLED_ORDERS = False
    ENABLE_SPOT_BUY_MARKET_WITH_COST = True
    REQUIRE_ORDER_FEES_FROM_TRADES = True  # set True when get_order is not giving fees on closed orders and fees
    # should be fetched using recent trades.

    @classmethod
    def get_name(cls):
        return 'lbank'

    def get_adapter_class(self):
        return LBankCCXTAdapter

    async def get_account_id(self, **kwargs: dict) -> str:
        # not supported
        return constants.DEFAULT_ACCOUNT_ID

    def get_additional_connector_config(self):
        # tell ccxt to use amount as provided and not to compute it by multiplying it by price which is done here
        # (price should not be sent to market orders). Only used for buy market orders
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "createMarketBuyOrderRequiresPrice": False  # disable quote conversion
            }
        }

    def is_authenticated_request(self, url: str, method: str, headers: dict, body) -> bool:
        body_signature_identifiers = "sign="
        header_signature_method_identifiers = "signature_method"
        return bool(
            headers
            and header_signature_method_identifiers in headers
        ) or bool(
            body
            and body_signature_identifiers in body
        )


class LBankCCXTAdapter(exchanges.CCXTAdapter):
    pass
