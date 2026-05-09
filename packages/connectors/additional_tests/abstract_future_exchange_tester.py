"""
Abstract tester for futures exchanges.
Mirrors packages/trading/tests_additional/real_exchanges/real_futures_exchange_tester.py
but delegates to the Rust connector via octobot_connectors.
"""
from .abstract_exchange_tester import AbstractExchangeTester


class AbstractFutureExchangeTester(AbstractExchangeTester):
    EXCHANGE_TYPE: str = "future"
    MARKET_STATUS_TYPE: str = "swap"
    PROFILE_ID = None

    # ---- Test entrypoints ----

    async def test_get_funding_rate(self):
        pass

    async def test_fetch_user_positions(self, **kwargs):
        pass

    async def test_fetch_user_closed_positions(self, **kwargs):
        pass

    # ---- Fetchers ----

    async def get_funding_rate(self, **kwargs):
        async with self.get_exchange_manager() as exchange:
            funding = exchange.get_funding_rate(self.SYMBOL)
            ticker = exchange.get_price_ticker(self.SYMBOL)
            return funding, ticker

    def _check_funding_rate(
        self,
        funding_rate,
        has_rate=True,
        has_last_time=True,
        has_next_rate=True,
        has_next_time=True,
        has_next_time_in_the_past=False,
    ):
        """
        Used data are
        - funding rate (value)
        - last_funding_time (timestamp)
        - predicted_funding_rate (value)
        - next_funding_time (timestamp)
        """
        assert funding_rate
        if has_rate:
            assert funding_rate.funding_rate is not None
        else:
            assert funding_rate.funding_rate is None
        if has_last_time:
            assert funding_rate.last_funding_time is not None
            assert 0 < funding_rate.last_funding_time <= self.get_time() * 1000
        else:
            assert funding_rate.last_funding_time in (None, 0)
        if has_next_rate:
            assert funding_rate.predicted_funding_rate is not None
        else:
            assert funding_rate.predicted_funding_rate is None
        if has_next_time_in_the_past:
            assert funding_rate.next_funding_time is not None
            assert funding_rate.next_funding_time < self.get_time() * 1000
        elif has_next_time:
            assert funding_rate.next_funding_time is not None
            assert funding_rate.next_funding_time >= self.get_time() * 1000
        else:
            assert funding_rate.next_funding_time in (None, 0)

    async def get_user_positions(self, **kwargs):
        async with self.get_exchange_manager() as exchange:
            return exchange.get_positions([self.SYMBOL])

    async def get_user_closed_positions(self, **kwargs):
        # Closed positions are not yet exposed by the Rust connector — best-effort.
        async with self.get_exchange_manager() as exchange:
            return exchange.get_positions([self.SYMBOL])

    def _check_position(self, position, check_symbol=False):
        assert position
        if check_symbol:
            assert position.symbol == self.SYMBOL
        else:
            assert position.symbol is not None
        assert position.contracts > 0
        assert position.entry_price is not None and position.entry_price > 0
        assert position.unrealised_pnl is not None
        assert position.initial_margin is not None and position.initial_margin > 0
        assert position.timestamp is not None and position.timestamp > 0
        assert position.mark_price is not None and position.mark_price > 0
        assert position.liquidation_price is not None and position.liquidation_price >= 0
        assert position.realised_pnl is not None
        assert position.notional is not None and position.notional >= 0
        assert position.collateral is not None and position.collateral >= 0
        assert position.maintenance_margin_percentage is not None \
            and position.maintenance_margin_percentage >= 0
        assert position.leverage is not None and position.leverage > 0
        assert position.margin_type is not None
        assert position.contract_size is not None
        assert position.side is not None
