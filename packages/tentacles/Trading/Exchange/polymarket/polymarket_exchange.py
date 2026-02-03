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
import datetime
import decimal
import typing

import octobot_trading.enums as enums
import octobot_trading.exchanges as exchanges
import octobot_trading.exchanges.connectors.ccxt.constants as ccxt_constants
import octobot_trading.exchanges.connectors.ccxt.enums as ccxt_enums


class PolymarketConnector(exchanges.CCXTConnector):

    def _client_factory(
        self,
        force_unauth,
        keys_adapter: typing.Callable[[exchanges.ExchangeCredentialsData], exchanges.ExchangeCredentialsData]=None
    ) -> tuple:
        return super()._client_factory(force_unauth, keys_adapter=self._keys_adapter)

    def _keys_adapter(self, creds: exchanges.ExchangeCredentialsData) -> exchanges.ExchangeCredentialsData:
        # if api key and secret are provided, use them as wallet address and private key
        creds.wallet_address = creds.api_key
        creds.uid = creds.password
        creds.private_key = creds.secret
        creds.api_key = creds.secret = creds.password = None
        return creds

    async def get_user_positions(self, user_id: str, symbols=None, **kwargs: dict) -> list:
        positions = []
        user_positions = await self.client.fetch_user_positions(user_id, symbols=symbols, params=kwargs)
        for position in user_positions:
            if not _is_position_expired(position):
                symbol = position.get(enums.ExchangeConstantsPositionColumns.SYMBOL.value)
                try:
                    positions.append(self.adapter.adapt_position(position))
                except Exception as e:
                    self.logger.error(f"Error adapting position: {e} (symbol: {symbol})")
        return positions


class Polymarket(exchanges.RestExchange):
    DESCRIPTION = ""
    DEFAULT_CONNECTOR_CLASS = PolymarketConnector

    SUPPORT_FETCHING_CANCELLED_ORDERS = False
    SUPPORTS_SET_MARGIN_TYPE = False

    @classmethod
    def get_name(cls):
        return 'polymarket'

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            enums.ExchangeTypes.OPTION,
        ]

    def get_additional_connector_config(self):
        return {
            ccxt_constants.CCXT_OPTIONS: {
                "fetchMarkets": {
                    "types": ["option"],  # only polymarket option markets are supported
                }
            }
        }
    
    async def get_price_ticker(self, symbol: str, **kwargs: dict) -> typing.Optional[dict]:
        if 'token_id' not in kwargs:
            try:
                market = self.connector.client.market(symbol)
                token_id = market.get('id')
                if token_id:
                    kwargs['token_id'] = token_id
            except Exception as e:
                self.logger.debug(f"Could not extract token_id for {symbol}: {e}")
        return await super().get_price_ticker(symbol, **kwargs)

    async def get_symbol_leverage(self, symbol: str, **kwargs: dict):
        return decimal.Decimal(1)
    
    async def get_margin_type(self, symbol: str):
        return ccxt_enums.ExchangeMarginTypes.CROSS

    async def get_funding_rate(self, symbol: str, **kwargs: dict):
        return decimal.Decimal(0.0)

    async def get_position_mode(self, symbol: str, **kwargs: dict):
        return enums.PositionMode.ONE_WAY
    
    async def get_maintenance_margin_rate(self, symbol: str):
        return decimal.Decimal(0.0)

    def get_contract_size(self, symbol: str):
        """
        Override contract size lookup for Polymarket.

        Polymarket positions are 1:1 "shares" settled in the quote currency (USDC).
        For expired or synthetic markets, the underlying CCXT client may not have
        a market entry for the full unified symbol, which would normally cause a
        KeyError when accessing client.markets[symbol].

        To keep index/copy-trading logic working for historical/closed markets
        (which only needs a consistent contract size, not the exact tick rules),
        we treat all Polymarket contracts as having size 1.
        """
        return decimal.Decimal(1)

    def is_linear_symbol(self, symbol) -> bool:
        """
        Override linear / inverse detection for Polymarket symbols.

        Polymarket markets are USDC-settled binary options, including expired
        markets that we may reconstruct synthetically. Their linearity does not
        depend on the presence of an active CCXT market entry, so we treat all
        Polymarket symbols as linear to avoid calling the underlying CCXT
        client's market() method for closed markets.
        """
        return True

    def is_inverse_symbol(self, symbol) -> bool:
        """
        Polymarket does not expose inverse-settled contracts.
        """
        return False

def _parse_end_date(end_date: str) -> typing.Optional[datetime.datetime]:
    try:
        parsed_date = datetime.datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if parsed_date.tzinfo is not None:
            parsed_date = parsed_date.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return parsed_date
    except (ValueError, AttributeError, TypeError):
        return None


def _is_position_expired(position):
    # is_redeemable = position.get("info", {}).get("redeemable") == False
    end_date_str = position.get("info", {}).get("endDate")
    if end_date_str is None:
        return False
    parsed_end_date = _parse_end_date(end_date_str)
    if parsed_end_date is None:
        return False
    is_ended = parsed_end_date < datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    return is_ended
