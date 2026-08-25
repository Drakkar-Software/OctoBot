import mock
import pytest

import octobot_trading.errors as trading_errors

import octobot_flow.repositories.exchange.transactions_repository as transactions_repository_module


def _make_repo(exchange_manager):
    fetched_data = mock.MagicMock()
    return transactions_repository_module.TransactionsRepository(exchange_manager, [], fetched_data)


class TestFetchDeposits:
    @pytest.mark.asyncio
    async def test_returns_deposits_when_supported(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange.get_deposits.return_value = [{"id": "d1"}]
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_deposits()
        assert result == [{"id": "d1"}]

    @pytest.mark.asyncio
    async def test_returns_empty_when_not_supported(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.exchange.get_deposits.side_effect = trading_errors.NotSupported("nope")
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_deposits()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_authentication_fails(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange_name = "kraken"
        exchange_manager.exchange.get_deposits.side_effect = trading_errors.AuthenticationError("denied")
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_deposits()
        assert result == []

    @pytest.mark.asyncio
    async def test_forwards_currencies_to_exchange_get_deposits(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange.get_deposits.return_value = [{"id": "d1"}]
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_deposits(currencies=["BTC", "ETH"])
        assert result == [{"id": "d1"}]
        exchange_manager.exchange.get_deposits.assert_awaited_once_with(
            since=None, limit=None, currencies=["BTC", "ETH"]
        )


class TestFetchWithdrawals:
    @pytest.mark.asyncio
    async def test_returns_withdrawals_when_supported(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange.get_withdrawals.return_value = [{"id": "w1"}]
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_withdrawals()
        assert result == [{"id": "w1"}]

    @pytest.mark.asyncio
    async def test_returns_empty_when_not_supported(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange_name = "binance"
        exchange_manager.exchange.get_withdrawals.side_effect = trading_errors.NotSupported("nope")
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_withdrawals()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_authentication_fails(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange_name = "kraken"
        exchange_manager.exchange.get_withdrawals.side_effect = trading_errors.AuthenticationError("denied")
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_withdrawals()
        assert result == []

    @pytest.mark.asyncio
    async def test_forwards_currencies_to_exchange_get_withdrawals(self):
        exchange_manager = mock.AsyncMock()
        exchange_manager.exchange.get_withdrawals.return_value = [{"id": "w1"}]
        repo = _make_repo(exchange_manager)
        result = await repo.fetch_withdrawals(currencies=["BTC", "ETH"])
        assert result == [{"id": "w1"}]
        exchange_manager.exchange.get_withdrawals.assert_awaited_once_with(
            since=None, limit=None, currencies=["BTC", "ETH"]
        )
