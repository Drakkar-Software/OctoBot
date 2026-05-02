import asyncio
import decimal
import json
import mock
import pytest
import pytest_asyncio

import async_channel.channels as async_channel_channels

import octobot_commons.json_util as json_util_module
import octobot_copy.entities as copy_entities

import octobot_flow.entities
import octobot_flow.repositories.community.trading_signals_channel as trading_signals_channel
import octobot_flow.repositories.community.trading_signals_repository as trading_signals_repository


@pytest.fixture
def internal_channel_name():
    return trading_signals_channel.InternalTradingSignalChannel.get_name()


@pytest.fixture(autouse=True)
def reset_internal_trading_signal_channel(internal_channel_name):
    async_channel_channels.del_chan(internal_channel_name)
    yield
    async_channel_channels.del_chan(internal_channel_name)


@pytest_asyncio.fixture(autouse=True)
async def shutdown_internal_trading_signal_channel_after_test(reset_internal_trading_signal_channel):
    """Ensure async channel teardown (stop / flush / del_chan) runs before sync reset del_chan."""
    try:
        yield
    finally:
        await trading_signals_channel.shutdown_internal_trading_signal_channel()


@pytest.mark.asyncio
async def test_insert_trading_signal_delivers_to_subscriber(internal_channel_name):
    received: list[octobot_flow.entities.TradingSignal] = []

    async def capture_callback(trading_signal: octobot_flow.entities.TradingSignal) -> None:
        received.append(trading_signal)

    channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await channel.new_consumer(capture_callback)

    account = copy_entities.Account()
    signal = octobot_flow.entities.TradingSignal(account=account, strategy_id="test-strategy-id")
    repository = trading_signals_repository.TradingSignalsRepository(mock.MagicMock())
    with mock.patch.object(
        repository,
        "_upload_trading_signal",
        mock.AsyncMock(),
    ) as mock_upload_signal:
        await repository.insert_trading_signal(signal)

    mock_upload_signal.assert_called_once_with(signal)

    await asyncio.sleep(0.05)
    assert len(received) == 1
    assert received[0] is signal


@pytest.mark.asyncio
async def test_get_or_create_internal_trading_signal_channel_is_idempotent(internal_channel_name):
    first = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    second = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert first is second


@pytest.mark.asyncio
async def test_shutdown_internal_trading_signal_channel_allows_recreate(internal_channel_name):
    await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    await trading_signals_channel.shutdown_internal_trading_signal_channel()
    with pytest.raises(KeyError):
        async_channel_channels.get_chan(internal_channel_name)

    new_channel = await trading_signals_channel.get_or_create_internal_trading_signal_channel()
    assert new_channel is not None


def _trading_signal(strategy_id: str, updated_at: float) -> octobot_flow.entities.TradingSignal:
    return octobot_flow.entities.TradingSignal(
        strategy_id=strategy_id,
        account=copy_entities.Account(updated_at=updated_at),
    )


def _payload_dict(*signals: octobot_flow.entities.TradingSignal) -> dict:
    return trading_signals_repository.TradingSignalPayload(signals=list(signals)).to_dict()


def _merge_result_updated_at_sequence(merged_dict: dict) -> list[float]:
    parsed = trading_signals_repository.TradingSignalPayload.from_dict(merged_dict)
    return [float(signal.account.updated_at) for signal in parsed.signals]


def _assert_no_decimal_leaves(value) -> None:
    """``_merge_trading_signal_documents`` wraps the merged dict in ``json_util.sanitize`` (no nested Decimal)."""
    if isinstance(value, dict):
        for nested in value.values():
            _assert_no_decimal_leaves(nested)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_decimal_leaves(item)
    else:
        assert not isinstance(value, decimal.Decimal), f"expected sanitized merge, got Decimal: {value!r}"


class TestMergeTradingSignalDocuments:
    """Covers ``_merge_trading_signal_documents``; results are ``json_util.sanitize(merged.to_dict())`` for Starfish push."""

    def test_both_empty_documents_yield_empty_signals(self):
        merged = trading_signals_repository._merge_trading_signal_documents({}, {})
        assert merged == json_util_module.sanitize({"signals": []})
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_empty_remote_yields_local_signals_sorted_chronologically(self):
        first_later = _trading_signal("s", 200.0)
        second_earlier = _trading_signal("s", 100.0)
        merged = trading_signals_repository._merge_trading_signal_documents(
            _payload_dict(first_later, second_earlier),
            {},
        )
        assert _merge_result_updated_at_sequence(merged) == [100.0, 200.0]
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_empty_local_yields_remote_signals_sorted_chronologically(self):
        remote_third = _trading_signal("s", 300.0)
        remote_first = _trading_signal("s", 100.0)
        remote_second = _trading_signal("s", 200.0)
        merged = trading_signals_repository._merge_trading_signal_documents(
            {},
            _payload_dict(remote_third, remote_first, remote_second),
        )
        assert _merge_result_updated_at_sequence(merged) == [100.0, 200.0, 300.0]
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_deduplicates_remote_then_appends_new_local_snapshots(self):
        remote_a = _trading_signal("strat", 1.0)
        remote_b = _trading_signal("strat", 2.0)
        local_a = _trading_signal("strat", 1.0)
        local_b = _trading_signal("strat", 2.0)
        local_c = _trading_signal("strat", 3.0)
        merged = trading_signals_repository._merge_trading_signal_documents(
            _payload_dict(local_a, local_b, local_c),
            _payload_dict(remote_a, remote_b),
        )
        assert _merge_result_updated_at_sequence(merged) == [1.0, 2.0, 3.0]
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_stable_order_when_two_signals_share_timestamp(self):
        first_at_tie = _trading_signal("strat", 50.0)
        second_at_tie = _trading_signal("strat", 50.0)
        merged = trading_signals_repository._merge_trading_signal_documents(
            {},
            _payload_dict(second_at_tie, first_at_tie),
        )
        sequence = _merge_result_updated_at_sequence(merged)
        assert sequence == [50.0, 50.0]
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_local_only_tail_sorted_when_new_signals_not_in_remote(self):
        remote_lo = _trading_signal("strat", 10.0)
        remote_hi = _trading_signal("strat", 20.0)
        local_newer_first_in_list = _trading_signal("strat", 50.0)
        local_newer_second_in_list = _trading_signal("strat", 40.0)
        merged = trading_signals_repository._merge_trading_signal_documents(
            _payload_dict(remote_lo, remote_hi, local_newer_first_in_list, local_newer_second_in_list),
            _payload_dict(remote_lo, remote_hi),
        )
        assert _merge_result_updated_at_sequence(merged) == [10.0, 20.0, 40.0, 50.0]
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)

    def test_merge_with_portfolio_decimals_is_sanitized(self):
        """Mirrors sync JSON: portfolio totals are Decimals in-domain but must become floats after merge."""
        account_with_decimals = copy_entities.Account(
            updated_at=1.0,
            content={
                "USDC": {"total": decimal.Decimal("1000.5"), "available": decimal.Decimal("1000.5")},
            },
        )
        signal = octobot_flow.entities.TradingSignal(strategy_id="s", account=account_with_decimals)
        merged = trading_signals_repository._merge_trading_signal_documents(
            _payload_dict(signal),
            {},
        )
        _assert_no_decimal_leaves(merged)
        json.dumps(merged)
        assert merged["signals"][0]["account"]["content"]["USDC"]["total"] == 1000.5
