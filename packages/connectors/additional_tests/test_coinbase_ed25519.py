import pytest
from .test_coinbase import CoinbaseTester

pytestmark = pytest.mark.asyncio


class CoinbaseEd25519Tester(CoinbaseTester):
    """Same exchange as Coinbase but uses ed25519 key credentials (COINBASE_ED25519_API_KEY env)."""
    EXCHANGE_NAME = "coinbase"

    def _load_credentials(self):
        import os
        from octobot_connectors import ExchangeCredentials
        key = os.environ.get("COINBASE_ED25519_API_KEY", "")
        secret = os.environ.get("COINBASE_ED25519_API_SECRET", "")
        return ExchangeCredentials(api_key=key, secret=secret)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinbase_ed25519_get_portfolio():
    await CoinbaseEd25519Tester().test_get_portfolio()


@pytest.mark.asyncio
async def test_coinbase_ed25519_get_symbol_prices():
    await CoinbaseEd25519Tester().test_get_symbol_prices()


@pytest.mark.slow
@pytest.mark.asyncio
async def test_coinbase_ed25519_get_open_orders():
    await CoinbaseEd25519Tester().test_get_open_orders()
