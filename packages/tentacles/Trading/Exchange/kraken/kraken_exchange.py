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
import octobot_trading.exchanges as exchanges


class Kraken(exchanges.RestExchange):
    """
    Kraken exchange connector.

    Portfolio history limitation (TradesHistory fees)
    -------------------------------------------------
    Kraken TradesHistory always reports the ``fee`` field in quote currency, even
    when the fee was actually deducted from base. See:
    https://support.kraken.com/hc/en-us/articles/360001184886

    CCXT ``kraken.parseTrade`` sets ``amount = vol`` and ``fee.currency = quote``.
    Portfolio history reverse-replay uses ``fee.currency`` to decide which leg is
    debited; when the currency is wrong, replay can show a small negative holding
    for an asset before its first trade (e.g. -1.18966e-05 BTC when vol is gross
    but the account was credited net of a base fee).

    Fee currency on Kraken orders (``oflags``)
    ------------------------------------------
    Kraken expresses fee-currency preference per order via ``oflags`` on order
    objects (not on trade history records):

    - ``fciq``: prefer fee in quote (default for buy orders)
    - ``fcib``: prefer fee in base (default for sell orders)

    CCXT ``kraken.parseOrder`` reads these flags; ``parseTrade`` does not,
    because TradesHistory fills only expose ``ordertxid`` — not ``oflags``.

    Why verified fees are not enriched on trades
    ------------------------------------------
    Correcting ``fee.currency`` / net base quantity would require Kraken-specific
    post-fetch enrichment, for example:

    - Batch ``QueryOrders`` by ``ordertxid`` to read ``oflags``, then convert the
      quote-denominated ``fee`` to base when ``fcib`` applies; or
    - Batch ledger lookups (``ledgers`` IDs on trades, or ``QueryLedgers``) for
      authoritative credited/debited amounts.

    Tradeoffs (intentionally not implemented):

    - Extra authenticated API calls on every portfolio-history sync (rate limits,
      latency, failure modes).
    - ``oflags`` is a preference, not a guarantee (Kraken may fall back if the
      chosen currency has insufficient balance); only ledger entries are exact.
    - Enrichment is exchange-specific; replay builder stays generic.

    Latest portfolio balances remain correct; only historical pre-trade snapshots
    for affected trades may be slightly wrong.
    """

    @classmethod
    def get_name(cls):
        return 'kraken'
