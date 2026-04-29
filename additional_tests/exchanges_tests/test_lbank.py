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
import pytest
import ccxt

import octobot_trading.errors as octobot_errors

from additional_tests.exchanges_tests import abstract_authenticated_exchange_tester

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


class TestLBankAuthenticatedExchange(
    abstract_authenticated_exchange_tester.AbstractAuthenticatedExchangeTester
):
    # enter exchange name as a class variable here
    EXCHANGE_NAME = "lbank"
    EXCHANGE_TENTACLE_NAME = "LBank"
    # WARNING: use a tradable symbol otherwise tests will fail
    # because of "ccxt.BadSymbol: Invalid Trading Pair" when cancelling order
    # due to https://github.com/LBank-exchange/lbank-official-api-docs/issues/29
    ORDER_CURRENCY = "BNB" # WARNING: use a tradable symbol (see test_untradable_symbols)
    SETTLEMENT_CURRENCY = "USDT"
    SYMBOL = f"{ORDER_CURRENCY}/{SETTLEMENT_CURRENCY}"
    ORDER_SIZE = 15  # % of portfolio to include in test orders
    VALID_ORDER_ID = "1777764898965454848"
    IS_ACCOUNT_ID_AVAILABLE = True  # set False when get_account_id is not available and should be checked
    EXPECTED_GENERATED_ACCOUNT_ID = True   # set True when account_id can't be fetch and a generated account id is used
    IS_AUTHENTICATED_REQUEST_CHECK_AVAILABLE = True    # set True when is_authenticated_request is implemented
    EXPECT_NOT_SUPPORTED_ERROR_WHEN_FETCHING_CANCELLED_ORDERS = True    # set True when fetching cancelled orders is not supported and should raise a NotSupported error
    CHECK_EMPTY_ACCOUNT = False  # set True when the account to check has no funds. Warning: does not check order
    # can't test for now due to country restrictions
    # parse/create/fill/cancel or portfolio & trades parsing
    CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = True

    async def test_get_portfolio(self):
        await super().test_get_portfolio()

    async def test_get_portfolio_with_market_filter(self):
        await super().test_get_portfolio_with_market_filter()

    async def test_untradable_symbols(self):
        # self.LIST_TRADABLE_SYMBOLS = True   # uncomment to list tradable symbols
        await super().test_untradable_symbols()

    async def test_get_max_orders_count(self):
        await super().test_get_max_orders_count()

    async def test_get_account_id(self):
        await super().test_get_account_id()

    async def test_is_authenticated_request(self):
        await super().test_is_authenticated_request()

    async def test_invalid_api_key_error(self):
        await super().test_invalid_api_key_error()

    async def test_get_api_key_permissions(self):
        await super().test_get_api_key_permissions()

    async def test_missing_trading_api_key_permissions(self):
        await super().test_missing_trading_api_key_permissions()

    async def test_api_key_ip_whitelist_error(self):
        # now working: invalid IP seems to work as well for reading operations
        await super().test_api_key_ip_whitelist_error()

    async def test_get_not_found_order(self):
        await super().test_get_not_found_order()

    async def test_is_valid_account(self):
        await super().test_is_valid_account()

    async def test_get_special_orders(self):
        await super().test_get_special_orders()

    async def test_create_and_cancel_limit_orders(self):
        await super().test_create_and_cancel_limit_orders()

    async def test_create_and_fill_market_orders(self):
        await super().test_create_and_fill_market_orders()

    async def test_get_my_recent_trades(self):
        await super().test_get_my_recent_trades()

    async def test_get_closed_orders(self):
        await super().test_get_closed_orders()

    async def test_get_cancelled_orders(self):
        await super().test_get_cancelled_orders()

    async def test_create_and_cancel_stop_orders(self):
        # pass if not implemented
        pass

    async def test_edit_limit_order(self):
        # pass if not implemented
        pass

    async def test_edit_stop_order(self):
        # pass if not implemented
        pass

    async def test_create_single_bundled_orders(self):
        # pass if not implemented
        pass

    async def test_create_double_bundled_orders(self):
        # pass if not implemented
        pass


# 15/01/2026
# Tradable symbols: 397/2093: ['GOATSEUS3L/USDT', 'GOATSEUS3S/USDT', 'DT/USDT', 'XR/USDT', 'XT/USDT', 'BMB/USDT', 'BNB/USDT', 'BNC/USDT', 'CGO/USDT', 'FAN/USDT', 'FEI/USDT', 'FXY/USDT', 'IVT/USDT', 'JBC/USDT', 'LFT/USDT', 'MCS/USDT', 'OVO/USDT', 'RIS/USDT', 'TRX/ETH', 'VIX/USDT', 'AGFI/USDT', 'AGIX/USDT', 'AP3X/USDT', 'AR3L/USDT', 'AR3S/USDT', 'BLUE/USDT', 'DBNU/USDT', 'HEGE/USDT', 'HFOF/USDT', 'ID3L/USDT', 'ID3S/USDT', 'IP3L/USDT', 'IP3S/USDT', 'LEMX/USDT', 'ME3L/USDT', 'ME3S/USDT', 'OP3L/USDT', 'OP3S/USDT', 'ROAM/USDT', 'SAFE/USDT', 'SCNT/USDT', 'SEYT/USDT', 'SIFT/USDT', 'TAP2/USDT', 'TOTT/USDT', 'WNGY/USDT', 'ACE3L/USDT', 'ACE3S/USDT', 'ADA3L/USDT', 'ADA3S/USDT', 'APE3L/USDT', 'APE3S/USDT', 'APT3L/USDT', 'APT3S/USDT', 'ARB3L/USDT', 'ARB3S/USDT', 'ATA3L/USDT', 'ATA3S/USDT', 'AXS3L/USDT', 'AXS3S/USDT', 'AXS5L/USDT', 'AXS5S/USDT', 'BAT3L/USDT', 'BAT3S/USDT', 'BCH3L/USDT', 'BCH3S/USDT', 'BCH5L/USDT', 'BCH5S/USDT', 'BEL3L/USDT', 'BEL3S/USDT', 'BNB3L/USDT', 'BNB3S/USDT', 'BSV3L/USDT', 'BSV3S/USDT', 'BSV5L/USDT', 'BSV5S/USDT', 'BTC3L/USDT', 'BTC3S/USDT', 'BTC5L/USDT', 'BTC5S/USDT', 'C983L/USDT', 'C983S/USDT', 'CAT3L/USDT', 'CAT3S/USDT', 'CFX3L/USDT', 'CFX3S/USDT', 'CHR3L/USDT', 'CHR3S/USDT', 'CHZ3L/USDT', 'CHZ3S/USDT', 'CRO3L/USDT', 'CRO3S/USDT', 'CRV3L/USDT', 'CRV3S/USDT', 'CRV5L/USDT', 'CRV5S/USDT', 'CTK3L/USDT', 'CTK3S/USDT', 'CVC3L/USDT', 'CVC3S/USDT', 'DGB3L/USDT', 'DGB3S/USDT', 'DOT3L/USDT', 'DOT3S/USDT', 'DOT5L/USDT', 'DOT5S/USDT', 'ENA3L/USDT', 'ENA3S/USDT', 'ENJ3L/USDT', 'ENJ3S/USDT', 'ENJ5L/USDT', 'ENJ5S/USDT', 'ENS3L/USDT', 'ENS3S/USDT', 'ETC3L/USDT', 'ETC3S/USDT', 'ETH3L/USDT', 'ETH3S/USDT', 'ETH5L/USDT', 'ETH5S/USDT', 'FIL3L/USDT', 'FIL3S/USDT', 'FIL5L/USDT', 'FIL5S/USDT', 'GMT3L/USDT', 'GMT3S/USDT', 'GRT3L/USDT', 'GRT3S/USDT', 'GTC3L/USDT', 'GTC3S/USDT', 'ICP3L/USDT', 'ICP3S/USDT', 'ICX3L/USDT', 'ICX3S/USDT', 'IMX3L/USDT', 'IMX3S/USDT', 'INJ3L/USDT', 'INJ3S/USDT', 'JASMY/USDT', 'KNC3L/USDT', 'KNC3S/USDT', 'KSM3L/USDT', 'KSM3S/USDT', 'LPT3L/USDT', 'LPT3S/USDT', 'LRC3L/USDT', 'LRC3S/USDT', 'LSETH/USDT', 'LTC3L/USDT', 'LTC3S/USDT', 'LTC5L/USDT', 'LTC5S/USDT', 'MBOOM/USDT', 'MTL3L/USDT', 'MTL3S/USDT', 'MYX3L/USDT', 'MYX3S/USDT', 'NEO3L/USDT', 'NEO3S/USDT', 'NEO5L/USDT', 'NEO5S/USDT', 'NKN3L/USDT', 'NKN3S/USDT', 'NOT3L/USDT', 'NOT3S/USDT', 'OGN3L/USDT', 'OGN3S/USDT', 'ONE3L/USDT', 'ONE3S/USDT', 'ONT3L/USDT', 'ONT3S/USDT', 'RAY3L/USDT', 'RAY3S/USDT', 'RIF3L/USDT', 'RIF3S/USDT', 'RLC3L/USDT', 'RLC3S/USDT', 'RSR3L/USDT', 'RSR3S/USDT', 'RVN3L/USDT', 'RVN3S/USDT', 'SFP3L/USDT', 'SFP3S/USDT', 'SKL3L/USDT', 'SKL3S/USDT', 'SNX3L/USDT', 'SNX3S/USDT', 'SOL3L/USDT', 'SOL3S/USDT', 'SOL5L/USDT', 'SOL5S/USDT', 'SPX3L/USDT', 'SPX3S/USDT', 'SSV3L/USDT', 'SSV3S/USDT', 'SUI3L/USDT', 'SUI3S/USDT', 'SXP3L/USDT', 'SXP3S/USDT', 'THE3L/USDT', 'THE3S/USDT', 'TIA3L/USDT', 'TIA3S/USDT', 'TLM3L/USDT', 'TLM3S/USDT', 'TON3L/USDT', 'TON3S/USDT', 'TRB3L/USDT', 'TRB3S/USDT', 'TRX3L/USDT', 'TRX3S/USDT', 'TRX5L/USDT', 'TRX5S/USDT', 'UNI3L/USDT', 'UNI3S/USDT', 'UNI5L/USDT', 'UNI5S/USDT', 'VET3L/USDT', 'VET3S/USDT', 'VNXAU/USDT', 'WIF3L/USDT', 'WIF3S/USDT', 'WLD3L/USDT', 'WLD3S/USDT', 'XLM3L/USDT', 'XLM3S/USDT', 'XMR3L/USDT', 'XMR3S/USDT', 'XRP3L/USDT', 'XRP3S/USDT', 'XRP5L/USDT', 'XRP5S/USDT', 'XTZ3L/USDT', 'XTZ3S/USDT', 'Y6D6S/VUSD', 'Y7D7S/VUSD', 'YFI3L/USDT', 'YFI3S/USDT', 'ZEC3L/USDT', 'ZEC3S/USDT', 'ZEN3L/USDT', 'ZEN3S/USDT', 'ZIL3L/USDT', 'ZIL3S/USDT', 'ZRX3L/USDT', 'ZRX3S/USDT', 'AAVE3L/USDT', 'AAVE3S/USDT', 'ALGO3L/USDT', 'ALGO3S/USDT', 'ANKR3L/USDT', 'ANKR3S/USDT', 'API33L/USDT', 'API33S/USDT', 'ARPA3L/USDT', 'ARPA3S/USDT', 'ATOM3L/USDT', 'ATOM3S/USDT', 'AVAX3L/USDT', 'AVAX3S/USDT', 'BAND3L/USDT', 'BAND3S/USDT', 'BOME3L/USDT', 'BOME3S/USDT', 'BONK3L/USDT', 'BONK3S/USDT', 'CELO3L/USDT', 'CELO3S/USDT', 'CELR3L/USDT', 'CELR3S/USDT', 'COMP3L/USDT', 'COMP3S/USDT', 'COTI3L/USDT', 'COTI3S/USDT', 'CTSI3L/USDT', 'CTSI3S/USDT', 'DASH3L/USDT', 'DASH3S/USDT', 'DENT3L/USDT', 'DENT3S/USDT', 'DOGE3L/USDT', 'DOGE3S/USDT', 'DOGE5L/USDT', 'DOGE5S/USDT', 'DOGS3L/USDT', 'DOGS3S/USDT', 'DYDX3L/USDT', 'DYDX3S/USDT', 'EGLD3L/USDT', 'EGLD3S/USDT', 'ELCASH/USDT', 'ENIDOG/USDT', 'FLOW3L/USDT', 'FLOW3S/USDT', 'GALA3L/USDT', 'GALA3S/USDT', 'GALA5L/USDT', 'GALA5S/USDT', 'HBAR3L/USDT', 'HBAR3S/USDT', 'HIGH3L/USDT', 'HIGH3S/USDT', 'HOOK3L/USDT', 'HOOK3S/USDT', 'IOST3L/USDT', 'IOST3S/USDT', 'IOTA3L/USDT', 'IOTA3S/USDT', 'IOTX3L/USDT', 'IOTX3S/USDT', 'KAVA3L/USDT', 'KAVA3S/USDT', 'LINK3L/USDT', 'LINK3S/USDT', 'LINK5L/USDT', 'LINK5S/USDT', 'MANA3L/USDT', 'MANA3S/USDT', 'MASK3L/USDT', 'MASK3S/USDT', 'NEAR3L/USDT', 'NEAR3S/USDT', 'PEPE3L/USDT', 'PEPE3S/USDT', 'PNUT3L/USDT', 'PNUT3S/USDT', 'QTUM3L/USDT', 'QTUM3S/USDT', 'ROSE3L/USDT', 'ROSE3S/USDT', 'RUNE3L/USDT', 'RUNE3S/USDT', 'SAND3L/USDT', 'SAND3S/USDT', 'SAND5L/USDT', 'SAND5S/USDT', 'SATS3L/USDT', 'SATS3S/USDT', 'SHIB3L/USDT', 'SHIB3S/USDT', 'SHIB5L/USDT', 'SHIB5S/USDT', 'STRK3L/USDT', 'STRK3S/USDT', 'VANA3L/USDT', 'VANA3S/USDT', 'VIGO1M/USDT', 'WLFI3L/USDT', 'WLFI3S/USDT', '1INCH3L/USDT', '1INCH3S/USDT', '1INCH5L/USDT', '1INCH5S/USDT', 'ALICE3L/USDT', 'ALICE3S/USDT', 'AUDIO3L/USDT', 'AUDIO3S/USDT', 'BELIEVE/USDT', 'FLOKI3L/USDT', 'FLOKI3S/USDT', 'GRASS3L/USDT', 'GRASS3S/USDT', 'JASMY3L/USDT', 'JASMY3S/USDT', 'MAGIC3L/USDT', 'MAGIC3S/USDT', 'PENGU3L/USDT', 'PENGU3S/USDT', 'PIXEL3L/USDT', 'PIXEL3S/USDT', 'SAITAMA/USDT', 'SPELL3L/USDT', 'SPELL3S/USDT', 'STORJ3L/USDT', 'STORJ3S/USDT', 'SUSHI3L/USDT', 'SUSHI3S/USDT', 'SUSHI5L/USDT', 'SUSHI5S/USDT', 'TESTBC1/VUSD', 'THETA3L/USDT', 'THETA3S/USDT', 'TRUMP3L/USDT', 'TRUMP3S/USDT', 'WAVES3L/USDT', 'WAVES3S/USDT', 'PEOPLE3L/USDT', 'PEOPLE3S/USDT', 'PEOPLE5L/USDT', 'PEOPLE5S/USDT', 'BIGTIME3L/USDT', 'BIGTIME3S/USDT', 'MELANIA3L/USDT', 'MELANIA3S/USDT', 'MOODENG3L/USDT', 'MOODENG3S/USDT', 'TESTPEPE2/VUSD']
