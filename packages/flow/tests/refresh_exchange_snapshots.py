"""Write offline binance and binanceus snapshots for flow functional tests.

Run from packages/flow so this tests package is imported ahead of the repository
root tests package:

    python -m tests.refresh_exchange_snapshots

Files land in tests/static/exchange_snapshots/. Functional tests load an
exchange from that directory when its file is present. Needs a network that
can reach the exchange.
"""

import argparse
import asyncio
import collections.abc
import pathlib

import ccxt.async_support as ccxt_async

import tests.exchange_snapshots as exchange_snapshot_lib


def ccxt_client(exchange_name: str):
    exchange_class = getattr(ccxt_async, exchange_name)
    return exchange_class({"enableRateLimit": True})


async def refresh_exchanges(
    exchange_names: collections.abc.Sequence[str],
    output_dir: pathlib.Path,
    client_factory: collections.abc.Callable[[str], object] = ccxt_client,
) -> list[pathlib.Path]:
    written = []
    for exchange_name in exchange_names:
        client = client_factory(exchange_name)
        try:
            snapshot = await exchange_snapshot_lib.capture_exchange_snapshot(client, exchange_name)
        finally:
            await client.close()
        written.append(exchange_snapshot_lib.dump_exchange_snapshot(snapshot, output_dir))
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh offline exchange snapshots for flow tests."
    )
    parser.add_argument(
        "--exchange",
        action="append",
        choices=exchange_snapshot_lib.SNAPSHOT_EXCHANGES,
        dest="exchanges",
        help="Exchange to refresh. Repeat for several. Defaults to binance and binanceus.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Directory for snapshot JSON files. Defaults to the flow tests static directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    exchange_names = (
        tuple(args.exchanges) if args.exchanges else exchange_snapshot_lib.SNAPSHOT_EXCHANGES
    )
    output_dir = args.output if args.output is not None else exchange_snapshot_lib.snapshots_root()
    written = asyncio.run(refresh_exchanges(exchange_names, output_dir))
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
