"""Offline binance and binanceus snapshots for flow functional tests.

The refresh script writes one JSON file per exchange under the flow tests static
directory. Functional tests do not read those files yet.
"""

import copy
import dataclasses
import datetime
import json
import pathlib

SNAPSHOT_VERSION = 1
SNAPSHOT_EXCHANGES = ("binance", "binanceus")
# Symbols the functional suite resolves on binance or binanceus.
SNAPSHOT_SYMBOLS = (
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BTC/USDC",
    "ETH/USDC",
    "SOL/USDC",
    "USDC/USDT",
    "USDC/USD",
)
# 1h and 2h cover trading-mode candles. 1d covers portfolio history.
SNAPSHOT_TIMEFRAMES = ("1h", "2h", "1d")
# Matches trading DEFAULT_CANDLES_HISTORY_SIZE (200) and covers the 180-day
# portfolio history lookback.
SNAPSHOT_CANDLE_LIMIT = 200
_OHLCV_ROW_LENGTH = 6
_STATIC_DIR_NAME = "static"
_SNAPSHOT_DIR_NAME = "exchange_snapshots"


class ExchangeSnapshotError(Exception):
    """Base error for offline exchange snapshots."""


class ExchangeSnapshotNotFound(ExchangeSnapshotError):
    """Raised when a snapshot file is missing."""


class ExchangeSnapshotInvalid(ExchangeSnapshotError):
    """Raised when a snapshot file or payload does not match the schema."""


@dataclasses.dataclass(frozen=True)
class ExchangeSnapshot:
    exchange: str
    captured_at: str
    symbols: tuple[str, ...]
    unavailable_symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    candle_limit: int
    markets: tuple[dict, ...]
    tickers: dict[str, dict]
    ohlcv: dict[str, dict[str, list]]

    def to_dict(self) -> dict:
        return {
            "version": SNAPSHOT_VERSION,
            "exchange": self.exchange,
            "captured_at": self.captured_at,
            "symbols": list(self.symbols),
            "unavailable_symbols": list(self.unavailable_symbols),
            "timeframes": list(self.timeframes),
            "candle_limit": self.candle_limit,
            "markets": list(self.markets),
            "tickers": self.tickers,
            "ohlcv": self.ohlcv,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ExchangeSnapshot":
        _validate_snapshot_payload(payload)
        return cls(
            exchange=payload["exchange"],
            captured_at=payload["captured_at"],
            symbols=tuple(payload["symbols"]),
            unavailable_symbols=tuple(payload["unavailable_symbols"]),
            timeframes=tuple(payload["timeframes"]),
            candle_limit=payload["candle_limit"],
            markets=tuple(payload["markets"]),
            tickers=payload["tickers"],
            ohlcv=payload["ohlcv"],
        )


def snapshots_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / _STATIC_DIR_NAME / _SNAPSHOT_DIR_NAME


def snapshot_path(exchange_name: str, root: pathlib.Path | None = None) -> pathlib.Path:
    _require_supported_exchange(exchange_name)
    directory = snapshots_root() if root is None else pathlib.Path(root)
    return directory / f"{exchange_name}.json"


def load_exchange_snapshot(
    exchange_name: str,
    root: pathlib.Path | None = None,
) -> ExchangeSnapshot:
    path = snapshot_path(exchange_name, root)
    if not path.is_file():
        raise ExchangeSnapshotNotFound(f"No snapshot file for {exchange_name} at {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ExchangeSnapshotInvalid(f"Snapshot for {exchange_name} is not valid JSON") from err
    try:
        return ExchangeSnapshot.from_dict(payload)
    except ExchangeSnapshotInvalid:
        raise
    except (KeyError, TypeError) as err:
        raise ExchangeSnapshotInvalid(f"Snapshot for {exchange_name} is incomplete") from err


def dump_exchange_snapshot(
    snapshot: ExchangeSnapshot,
    root: pathlib.Path | None = None,
) -> pathlib.Path:
    directory = snapshots_root() if root is None else pathlib.Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(snapshot.exchange, directory)
    payload = json.dumps(snapshot.to_dict(), indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
    return path


def install_snapshot_fetches(client, snapshot: ExchangeSnapshot) -> None:
    """Replace public market fetches on a ccxt-like client with snapshot data."""
    markets = copy.deepcopy(list(snapshot.markets))
    tickers = copy.deepcopy(snapshot.tickers)
    ohlcv = copy.deepcopy(snapshot.ohlcv)

    async def fetch_markets(params=None):
        return copy.deepcopy(markets)

    async def fetch_tickers(symbols=None, params=None):
        if symbols is None:
            return copy.deepcopy(tickers)
        missing = [symbol for symbol in symbols if symbol not in tickers]
        if missing:
            raise ExchangeSnapshotError(
                f"{snapshot.exchange} snapshot has no tickers for {missing}"
            )
        return {symbol: copy.deepcopy(tickers[symbol]) for symbol in symbols}

    async def fetch_ticker(symbol, params=None):
        fetched = await fetch_tickers([symbol])
        return fetched[symbol]

    async def fetch_ohlcv(symbol, timeframe="1m", since=None, limit=None, params=None):
        try:
            rows = ohlcv[symbol][timeframe]
        except KeyError as err:
            raise ExchangeSnapshotError(
                f"{snapshot.exchange} snapshot has no {timeframe} ohlcv for {symbol}"
            ) from err
        selected = rows
        if since is not None:
            selected = [row for row in selected if row[0] >= since]
            if limit is not None:
                selected = selected[:limit]
        elif limit is not None:
            selected = selected[-limit:]
        return copy.deepcopy(selected)

    client.fetch_markets = fetch_markets
    client.fetch_tickers = fetch_tickers
    client.fetch_ticker = fetch_ticker
    client.fetch_ohlcv = fetch_ohlcv


async def capture_exchange_snapshot(
    client,
    exchange_name: str,
    captured_at: str | None = None,
) -> ExchangeSnapshot:
    """Record markets, tickers, and OHLCV for the functional-test symbol set."""
    _require_supported_exchange(exchange_name)
    raw_markets = await client.fetch_markets()
    markets, unavailable_symbols = _select_markets(raw_markets)
    if not markets:
        raise ExchangeSnapshotError(f"No snapshot symbols found on {exchange_name}")
    symbols = tuple(market["symbol"] for market in markets)
    try:
        raw_tickers = await client.fetch_tickers(list(symbols))
    except Exception as err:
        raise ExchangeSnapshotError(f"Failed to fetch {exchange_name} tickers") from err
    tickers = {}
    for symbol in symbols:
        ticker = raw_tickers.get(symbol) if isinstance(raw_tickers, dict) else None
        if not isinstance(ticker, dict):
            raise ExchangeSnapshotError(f"{exchange_name} returned no ticker for {symbol}")
        tickers[symbol] = ticker
    ohlcv: dict[str, dict[str, list]] = {}
    for symbol in symbols:
        ohlcv[symbol] = {}
        for timeframe in SNAPSHOT_TIMEFRAMES:
            try:
                rows = await client.fetch_ohlcv(symbol, timeframe, limit=SNAPSHOT_CANDLE_LIMIT)
            except Exception as err:
                raise ExchangeSnapshotError(
                    f"Failed to fetch {exchange_name} {symbol} {timeframe} ohlcv"
                ) from err
            if not rows:
                raise ExchangeSnapshotError(
                    f"{exchange_name} returned no {timeframe} ohlcv for {symbol}"
                )
            ohlcv[symbol][timeframe] = rows
    captured = captured_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = _json_roundtrip(
        {
            "version": SNAPSHOT_VERSION,
            "exchange": exchange_name,
            "captured_at": captured,
            "symbols": list(symbols),
            "unavailable_symbols": list(unavailable_symbols),
            "timeframes": list(SNAPSHOT_TIMEFRAMES),
            "candle_limit": SNAPSHOT_CANDLE_LIMIT,
            "markets": markets,
            "tickers": tickers,
            "ohlcv": ohlcv,
        },
        exchange_name,
    )
    return ExchangeSnapshot.from_dict(payload)


def _require_supported_exchange(exchange_name: str) -> None:
    if exchange_name not in SNAPSHOT_EXCHANGES:
        raise ExchangeSnapshotError(f"Unsupported exchange {exchange_name}")


def _select_markets(raw_markets) -> tuple[list, tuple[str, ...]]:
    if not isinstance(raw_markets, list):
        raise ExchangeSnapshotError("fetch_markets did not return a list")
    by_symbol = {}
    for market in raw_markets:
        if not isinstance(market, dict):
            continue
        symbol = market.get("symbol")
        if symbol not in SNAPSHOT_SYMBOLS or market.get("spot") is False:
            continue
        by_symbol.setdefault(symbol, market)
    symbols = [symbol for symbol in SNAPSHOT_SYMBOLS if symbol in by_symbol]
    unavailable = tuple(symbol for symbol in SNAPSHOT_SYMBOLS if symbol not in by_symbol)
    return [by_symbol[symbol] for symbol in symbols], unavailable


def _json_roundtrip(value, exchange_name: str):
    try:
        return json.loads(json.dumps(value))
    except TypeError as err:
        raise ExchangeSnapshotInvalid(f"{exchange_name} snapshot is not JSON-serializable") from err


def _validate_snapshot_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ExchangeSnapshotInvalid("Snapshot root must be an object")
    if payload.get("version") != SNAPSHOT_VERSION:
        raise ExchangeSnapshotInvalid(f"Unsupported snapshot version {payload.get('version')}")
    exchange_name = payload.get("exchange")
    if exchange_name not in SNAPSHOT_EXCHANGES:
        raise ExchangeSnapshotInvalid(f"Unsupported snapshot exchange {exchange_name}")
    captured_at = payload.get("captured_at")
    if not isinstance(captured_at, str) or not captured_at:
        raise ExchangeSnapshotInvalid("Snapshot captured_at must be a non-empty string")
    symbols = _require_str_tuple(payload.get("symbols"), "symbols")
    unavailable = _require_str_tuple(payload.get("unavailable_symbols"), "unavailable_symbols")
    if set(symbols) & set(unavailable):
        raise ExchangeSnapshotInvalid("Snapshot symbols and unavailable_symbols overlap")
    timeframes = _require_str_tuple(payload.get("timeframes"), "timeframes")
    if not timeframes:
        raise ExchangeSnapshotInvalid("Snapshot timeframes must not be empty")
    candle_limit = payload.get("candle_limit")
    if not isinstance(candle_limit, int) or isinstance(candle_limit, bool) or candle_limit < 1:
        raise ExchangeSnapshotInvalid("Snapshot candle_limit must be a positive integer")
    markets = payload.get("markets")
    if not isinstance(markets, list) or len(markets) != len(symbols):
        raise ExchangeSnapshotInvalid("Snapshot markets must match symbols")
    for symbol, market in zip(symbols, markets):
        if not isinstance(market, dict) or market.get("symbol") != symbol:
            raise ExchangeSnapshotInvalid(f"Snapshot market for {symbol} is missing")
    tickers = payload.get("tickers")
    if not isinstance(tickers, dict) or set(tickers) != set(symbols):
        raise ExchangeSnapshotInvalid("Snapshot tickers must match symbols")
    for symbol in symbols:
        if not isinstance(tickers[symbol], dict):
            raise ExchangeSnapshotInvalid(f"Snapshot ticker for {symbol} must be an object")
    ohlcv = payload.get("ohlcv")
    if not isinstance(ohlcv, dict) or set(ohlcv) != set(symbols):
        raise ExchangeSnapshotInvalid("Snapshot ohlcv must match symbols")
    for symbol in symbols:
        frames = ohlcv[symbol]
        if not isinstance(frames, dict) or set(frames) != set(timeframes):
            raise ExchangeSnapshotInvalid(f"Snapshot ohlcv timeframes for {symbol} do not match")
        for timeframe in timeframes:
            _validate_ohlcv_rows(frames[timeframe], symbol, timeframe)


def _require_str_tuple(value, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExchangeSnapshotInvalid(f"Snapshot {field_name} must be a list of strings")
    if len(value) != len(set(value)):
        raise ExchangeSnapshotInvalid(f"Snapshot {field_name} contains duplicates")
    return tuple(value)


def _validate_ohlcv_rows(rows, symbol: str, timeframe: str) -> None:
    if not isinstance(rows, list) or not rows:
        raise ExchangeSnapshotInvalid(
            f"Snapshot ohlcv for {symbol} {timeframe} must be a non-empty list"
        )
    for row in rows:
        if not isinstance(row, list) or len(row) < _OHLCV_ROW_LENGTH:
            raise ExchangeSnapshotInvalid(
                f"Snapshot ohlcv row for {symbol} {timeframe} is too short"
            )
        if not isinstance(row[0], (int, float)) or isinstance(row[0], bool):
            raise ExchangeSnapshotInvalid(
                f"Snapshot ohlcv timestamp for {symbol} {timeframe} is invalid"
            )
