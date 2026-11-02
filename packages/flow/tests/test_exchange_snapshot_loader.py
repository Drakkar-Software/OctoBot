import pytest

import tests.exchange_snapshots as exchange_snapshot_lib
import tests.refresh_exchange_snapshots as refresh_exchange_snapshot_lib


class _FakeClient:
    def __init__(self, markets, *, fail_ohlcv: bool = False, empty_ohlcv: bool = False):
        self._markets = markets
        self.fail_ohlcv = fail_ohlcv
        self.empty_ohlcv = empty_ohlcv
        self.closed = False
        self.ticker_symbols = None
        self.ohlcv_limit = None

    async def fetch_markets(self):
        return self._markets

    async def fetch_tickers(self, symbols):
        self.ticker_symbols = list(symbols)
        return {symbol: {"symbol": symbol, "last": 10.0, "close": 10.0} for symbol in symbols}

    async def fetch_ohlcv(self, symbol, timeframe, limit):
        self.ohlcv_limit = limit
        if self.fail_ohlcv:
            raise RuntimeError("ohlcv down")
        if self.empty_ohlcv:
            return []
        return [[1_700_000_000_000, 1, 2, 0.5, 1.5, 3]]

    async def close(self):
        self.closed = True


def _market(symbol: str, *, spot: bool = True) -> dict:
    return {"symbol": symbol, "spot": spot, "id": symbol.replace("/", "")}


def _sample_markets() -> list:
    return [
        _market("BTC/USDT"),
        _market("DOGE/USDT"),
        _market("ETH/USDT", spot=False),
        {"symbol": "ETH/USDC", "id": "ETHUSDC"},
        "not-a-market",
    ]


@pytest.mark.asyncio
async def test_capture_keeps_spot_symbols_and_records_the_rest():
    client = _FakeClient(_sample_markets())
    snapshot = await exchange_snapshot_lib.capture_exchange_snapshot(
        client,
        "binance",
        captured_at="2026-10-13T00:00:00+00:00",
    )
    assert snapshot.symbols == ("BTC/USDT", "ETH/USDC")
    assert "ETH/USDT" in snapshot.unavailable_symbols
    assert "DOGE/USDT" not in snapshot.symbols
    assert "DOGE/USDT" not in snapshot.unavailable_symbols
    assert client.ticker_symbols == ["BTC/USDT", "ETH/USDC"]
    assert client.ohlcv_limit == exchange_snapshot_lib.SNAPSHOT_CANDLE_LIMIT
    assert set(snapshot.ohlcv["BTC/USDT"]) == set(exchange_snapshot_lib.SNAPSHOT_TIMEFRAMES)


@pytest.mark.asyncio
async def test_capture_rejects_an_exchange_with_no_snapshot_symbols():
    client = _FakeClient([_market("DOGE/USDT")])
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="No snapshot symbols"):
        await exchange_snapshot_lib.capture_exchange_snapshot(client, "binanceus")


@pytest.mark.asyncio
async def test_capture_wraps_ohlcv_failures():
    client = _FakeClient([_market("BTC/USDT")], fail_ohlcv=True)
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="ohlcv"):
        await exchange_snapshot_lib.capture_exchange_snapshot(client, "binance")


@pytest.mark.asyncio
async def test_capture_rejects_empty_ohlcv():
    client = _FakeClient([_market("BTC/USDT")], empty_ohlcv=True)
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="no 1h ohlcv"):
        await exchange_snapshot_lib.capture_exchange_snapshot(client, "binance")


def test_dump_and_load_roundtrip(tmp_path):
    snapshot = exchange_snapshot_lib.ExchangeSnapshot.from_dict(
        {
            "version": exchange_snapshot_lib.SNAPSHOT_VERSION,
            "exchange": "binanceus",
            "captured_at": "2026-10-13T00:00:00+00:00",
            "symbols": ["BTC/USDT"],
            "unavailable_symbols": ["USDC/USD"],
            "timeframes": ["1h"],
            "candle_limit": 2,
            "markets": [{"symbol": "BTC/USDT", "spot": True}],
            "tickers": {"BTC/USDT": {"symbol": "BTC/USDT", "last": 20, "close": 20}},
            "ohlcv": {"BTC/USDT": {"1h": [[100, 1, 2, 0.5, 1.5, 3], [200, 1, 2, 0.5, 1.5, 3]]}},
        }
    )
    path = exchange_snapshot_lib.dump_exchange_snapshot(snapshot, tmp_path)
    assert path.name == "binanceus.json"
    assert not path.with_suffix(".json.tmp").exists()
    loaded = exchange_snapshot_lib.load_exchange_snapshot("binanceus", tmp_path)
    assert loaded == snapshot


def test_load_missing_snapshot(tmp_path):
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotNotFound):
        exchange_snapshot_lib.load_exchange_snapshot("binance", tmp_path)


def test_load_rejects_unknown_version(tmp_path):
    path = tmp_path / "binance.json"
    path.write_text('{"version": 99, "exchange": "binance"}\n', encoding="utf-8")
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotInvalid, match="version"):
        exchange_snapshot_lib.load_exchange_snapshot("binance", tmp_path)


def test_load_rejects_invalid_json(tmp_path):
    path = tmp_path / "binance.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotInvalid, match="not valid JSON"):
        exchange_snapshot_lib.load_exchange_snapshot("binance", tmp_path)


def test_unsupported_exchange_is_rejected():
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="Unsupported exchange"):
        exchange_snapshot_lib.snapshot_path("coinrabbit")


def test_snapshots_root_is_the_flow_tests_static_dir():
    root = exchange_snapshot_lib.snapshots_root()
    assert root.name == "exchange_snapshots"
    assert root.parent.name == "static"
    assert root.parent.parent.name == "tests"


@pytest.mark.asyncio
async def test_install_snapshot_fetches_serves_markets_tickers_and_ohlcv():
    snapshot = exchange_snapshot_lib.ExchangeSnapshot.from_dict(
        {
            "version": 1,
            "exchange": "binance",
            "captured_at": "2026-10-13T00:00:00+00:00",
            "symbols": ["BTC/USDT"],
            "unavailable_symbols": [],
            "timeframes": ["1h"],
            "candle_limit": 4,
            "markets": [{"symbol": "BTC/USDT", "precision": {"price": 2}}],
            "tickers": {"BTC/USDT": {"last": 30, "close": 30}},
            "ohlcv": {
                "BTC/USDT": {
                    "1h": [
                        [100, 1, 1, 1, 1, 1],
                        [200, 1, 1, 1, 1, 1],
                        [300, 1, 1, 1, 1, 1],
                        [400, 1, 1, 1, 1, 1],
                    ]
                }
            },
        }
    )
    client = _FakeClient([])
    exchange_snapshot_lib.install_snapshot_fetches(client, snapshot)
    markets = await client.fetch_markets()
    markets[0]["precision"]["price"] = 0
    assert (await client.fetch_markets())[0]["precision"]["price"] == 2
    assert (await client.fetch_ticker("BTC/USDT"))["close"] == 30
    assert await client.fetch_ohlcv("BTC/USDT", "1h", limit=2) == [
        [300, 1, 1, 1, 1, 1],
        [400, 1, 1, 1, 1, 1],
    ]
    assert await client.fetch_ohlcv("BTC/USDT", "1h", since=200, limit=1) == [[200, 1, 1, 1, 1, 1]]
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="ETH/USDT"):
        await client.fetch_ticker("ETH/USDT")
    with pytest.raises(exchange_snapshot_lib.ExchangeSnapshotError, match="1d"):
        await client.fetch_ohlcv("BTC/USDT", "1d")


@pytest.mark.asyncio
async def test_refresh_exchanges_closes_the_client_and_writes_the_file(tmp_path):
    client = _FakeClient([_market("BTC/USDT")])

    def _factory(exchange_name):
        assert exchange_name == "binance"
        return client

    written = await refresh_exchange_snapshot_lib.refresh_exchanges(
        ("binance",), tmp_path, _factory
    )
    assert client.closed is True
    assert written == [tmp_path / "binance.json"]
    loaded = exchange_snapshot_lib.load_exchange_snapshot("binance", tmp_path)
    assert loaded.symbols == ("BTC/USDT",)


def test_parse_args_defaults_to_both_exchanges_and_the_static_dir():
    args = refresh_exchange_snapshot_lib.parse_args([])
    assert args.exchanges is None
    assert args.output is None
    names = tuple(args.exchanges) if args.exchanges else exchange_snapshot_lib.SNAPSHOT_EXCHANGES
    assert names == ("binance", "binanceus")


def _committed_binanceus_snapshot() -> exchange_snapshot_lib.ExchangeSnapshot:
    return exchange_snapshot_lib.ExchangeSnapshot.from_dict(
        {
            "version": 1,
            "exchange": "binanceus",
            "captured_at": "2026-10-13T00:00:00+00:00",
            "symbols": ["BTC/USDT"],
            "unavailable_symbols": [],
            "timeframes": ["1h"],
            "candle_limit": 1,
            "markets": [{"symbol": "BTC/USDT", "spot": True}],
            "tickers": {"BTC/USDT": {"last": 11, "close": 11}},
            "ohlcv": {"BTC/USDT": {"1h": [[100, 1, 1, 1, 1, 1]]}},
        }
    )


@pytest.mark.asyncio
async def test_apply_committed_snapshots_skips_exchanges_without_a_file(tmp_path):
    exchange_snapshot_lib.dump_exchange_snapshot(_committed_binanceus_snapshot(), tmp_path)

    class _Binance:
        def __init__(self, config=None):
            self.config = config

    class _BinanceUS(_Binance):
        pass

    class _ObBinanceUS(_BinanceUS):
        pass

    module = type("CCXT", (), {"binance": _Binance, "binanceus": _BinanceUS})
    patched = exchange_snapshot_lib.apply_committed_exchange_snapshots(module, tmp_path)
    try:
        assert patched == (_BinanceUS,)
        assert exchange_snapshot_lib.apply_committed_exchange_snapshots(module, tmp_path) == ()
        live = module.binance({})
        assert not hasattr(live, "fetch_markets")
        client = _ObBinanceUS({})
        assert (await client.fetch_markets())[0]["symbol"] == "BTC/USDT"
        assert (await client.fetch_ticker("BTC/USDT"))["close"] == 11
    finally:
        exchange_snapshot_lib.restore_committed_exchange_snapshots(patched)
    restored = _ObBinanceUS({})
    assert not hasattr(restored, "fetch_markets")
