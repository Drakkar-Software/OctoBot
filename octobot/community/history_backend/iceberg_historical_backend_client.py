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
import typing
import enum
import datetime
import os
import asyncio
import concurrent.futures
import logging
import json
import time

import pyarrow
import pyiceberg.catalog
import pyiceberg.schema
import pyiceberg.types
import pyiceberg.exceptions
import pyiceberg.expressions
import pyiceberg.table
import pyiceberg.table.sorting
import pyiceberg.table.statistics

import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot.constants as constants
import octobot.community.history_backend.historical_backend_client as historical_backend_client
import octobot.community.history_backend.util as history_backend_util
import octobot_commons.os_util as os_util


# avoid "Loaded FileIO: pyiceberg.io.pyarrow.PyArrowFileIO" info logs
logging.getLogger("pyiceberg.io").setLevel(logging.WARNING)


class TableNames(enum.Enum):
    OHLCV_HISTORY = constants.ICEBERG_OHLCV_HISTORY_TABLE


# pyiceberg itself uses a thread pool so each thread will create children threads, limit the number of "master" threads
_MAX_EXECUTOR_WORKERS = min(4, (os.cpu_count() or 1)) # use a max of 4 workers
_METADATA_SEPARATOR = "|"
_METADATA_VERSION = "1.0.0"
_MAX_STATISTICS_FILES = 10 # keep only the last X statistics files

class _MetadataIdentifiers(enum.Enum):
    UPDATED_AT = "updated_at"
    VERSION = "version"


class IcebergHistoricalBackendClient(historical_backend_client.HistoricalBackendClient):

    def __init__(self):
        self.namespace: typing.Optional[str] = None
        self.catalog: pyiceberg.catalog.Catalog = None # type: ignore
        self._executor: typing.Optional[concurrent.futures.ThreadPoolExecutor] = None # only availble when client is open
        self._fetching_candles_history_range: asyncio.Lock() = None # type: ignore
        self._fetched_min_max_per_symbol_per_time_frame_per_exchange: typing.Optional[
            dict[str, dict[str, dict[str, tuple[float, float]]]]
        ] = None
        self._updated_min_max_per_symbol_per_time_frame_per_exchange: typing.Optional[
            dict[str, dict[str, dict[str, tuple[float, float]]]]
        ] = None

    async def open(self):
        try:
            self._fetched_min_max_per_symbol_per_time_frame_per_exchange = None
            self._updated_min_max_per_symbol_per_time_frame_per_exchange = None
            self._fetching_candles_history_range = asyncio.Lock()
            self._executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=_MAX_EXECUTOR_WORKERS,
                thread_name_prefix="IcebergHistoricalBackendClient"
            )
            self.catalog = self._load_catalog()
        except Exception as err:
            message = f"Error when connecting to Iceberg server, {err.__class__.__name__}: {err}"
            self._get_logger().exception(err, True, message)
            raise err.__class__(message) from err

    async def close(self):
        if self._executor is not None:
            if self._has_metadata_to_update():
                # should always be called when metadata have to be updated 
                # otherwise their update will be lost and candle ranges won't be updated
                await self._update_metadata()
            self._updated_min_max_per_symbol_per_time_frame_per_exchange = None
            self._fetched_min_max_per_symbol_per_time_frame_per_exchange = None
            self._executor.shutdown()
        self._fetching_candles_history_range = None
        self._executor = None

    async def _run_in_executor(self, func, *args):
        if self._executor is None:
            raise ValueError(f"{self.__class__.__name__} is not open")
        # run blocking IO code in a dedicated thread poool executor that is shutdown on close 
        # to avoid leaving threads alive when the client is closed
        return await asyncio.get_running_loop().run_in_executor(self._executor, func, *args)

    async def fetch_candles_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        first_open_time: float,
        last_open_time: float
    ) -> list[list[float]]:
        return await self._run_in_executor(
            self._sync_fetch_candles_history, 
            exchange, symbol, time_frame, None, None, first_open_time, last_open_time,
            False
        )

    async def fetch_extended_candles_history(
        self,
        exchange: str,
        symbols: list[str],
        time_frames: list[commons_enums.TimeFrames],
        first_open_time: typing.Optional[float] = None,
        last_open_time: typing.Optional[float] = None,
    ) -> list[list[typing.Union[float, str]]]:
        return await self._run_in_executor(
            self._sync_fetch_candles_history, 
            exchange, None, None, symbols, time_frames, first_open_time, last_open_time,
            True
        )

    def _get_filter(
        self, element: str, value: typing.Union[None, str, list[str]]
    ) -> typing.Optional[pyiceberg.expressions.BooleanExpression]:
        if value is None:
            return None
        if isinstance(value, list):
            if len(value) > 1:
                return pyiceberg.expressions.Or(*(pyiceberg.expressions.EqualTo(element, _value) for _value in value))
            return pyiceberg.expressions.EqualTo(element, value[0])
        return pyiceberg.expressions.EqualTo(element, value)


    def _sync_fetch_candles_history(
        self,
        exchange: str,
        symbol: typing.Optional[str],
        time_frame: typing.Optional[commons_enums.TimeFrames],
        symbols: typing.Optional[list[str]],
        time_frames: typing.Optional[list[commons_enums.TimeFrames]],
        first_open_time: typing.Optional[float],
        last_open_time: typing.Optional[float],
        extended: bool,
    ) -> list[list[typing.Union[float, str]]]:
        table = self._get_or_create_table(TableNames.OHLCV_HISTORY)
        and_filters = [
            pyiceberg.expressions.EqualTo("exchange_internal_name", exchange),
        ]
        if tf_filter := self._get_filter(
            "time_frame", 
            [tf.value for tf in time_frames] if time_frames else time_frame.value if time_frame else None
        ):
            and_filters.append(tf_filter)
        if symbol_filter := self._get_filter("symbol", symbol or symbols):
            and_filters.append(symbol_filter)
        if first_open_time:
            and_filters.append(pyiceberg.expressions.GreaterThanOrEqual("timestamp", self.get_formatted_time(first_open_time)))
        if last_open_time:
            and_filters.append(pyiceberg.expressions.LessThanOrEqual("timestamp", self.get_formatted_time(last_open_time)))
        filter = pyiceberg.expressions.And(*and_filters) # pylint: disable=no-value-for-parameter
        selected_fields = ["timestamp", "open", "high", "low", "close", "volume"]
        if extended:
            selected_fields = ["time_frame", "symbol"] + selected_fields
        result = table.scan(
            row_filter=filter,
            selected_fields=selected_fields,
            case_sensitive=True,
        )

        formatted = self._format_ohlcvs(result.to_arrow(), extended)
        # ensure no duplicates as they can happen due to no unicity constraint
        return history_backend_util.deduplicate(formatted, [0, 1, 2] if extended else [0])

    async def fetch_candles_history_range(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
    ) -> tuple[float, float]:
        if self._fetched_min_max_per_symbol_per_time_frame_per_exchange is None:
            async with self._fetching_candles_history_range:
                # now that lock is acquired, check again if metadata still needs to be fetched
                if self._fetched_min_max_per_symbol_per_time_frame_per_exchange is None:
                    # fetches table metadata: do it in executor to avoid blocking the main thread
                    table = await self._run_in_executor(
                        self._get_or_create_table, TableNames.OHLCV_HISTORY
                    )
                    self._fetched_min_max_per_symbol_per_time_frame_per_exchange = self._parse_min_max_per_symbol_per_time_frame_per_exchange(
                        table
                    )
            if not self._fetched_min_max_per_symbol_per_time_frame_per_exchange:
                return (0, 0)

        return self._get_latest_min_max_per_symbol_per_time_frame_per_exchange(exchange, symbol, time_frame)

    def _get_latest_min_max_per_symbol_per_time_frame_per_exchange(
        self, exchange: str, symbol: str, time_frame: commons_enums.TimeFrames
    ) -> tuple[float, float]:
        if self._updated_min_max_per_symbol_per_time_frame_per_exchange and (
            min_max := self._updated_min_max_per_symbol_per_time_frame_per_exchange.get(exchange, {}).get(symbol, {}).get(time_frame.value)
        ):
            return min_max
        if not self._fetched_min_max_per_symbol_per_time_frame_per_exchange:
            return (0, 0)
        return self._fetched_min_max_per_symbol_per_time_frame_per_exchange.get(exchange, {}).get(symbol, {}).get(time_frame.value) or (0, 0)

    async def fetch_all_candles_for_exchange(self, exchange: str) -> list[list[typing.Union[float, str]]]:
        return await self._run_in_executor(
            self._sync_fetch_all_candles_for_exchange,
            exchange
        )

    def _sync_fetch_all_candles_for_exchange(self, exchange: str) -> list[list[typing.Union[float, str]]]:
        table = self._get_or_create_table(TableNames.OHLCV_HISTORY)
        selected_fields = ("timestamp", "symbol", "time_frame", "open", "high", "low", "close", "volume")
        scan = self._scan_all_candles_for_exchange(table, exchange, selected_fields)
        return self._format_ohlcvs(scan.to_arrow(), True)

    async def insert_candles_history(self, rows: list, column_names: list) -> None:
        await self._run_in_executor(
            self._sync_insert_candles_history,
            rows, column_names
        )

    def _sync_insert_candles_history(self, rows: list, column_names: list) -> None:
        if not rows:
            return
        schema = self._pyarrow_get_ohlcv_schema()
        table = self._get_or_create_table(TableNames.OHLCV_HISTORY)
        pa_arrays = [
            pyarrow.array([
                row[i]
                for row in rows
            ]) 
            for i, _ in enumerate(column_names)
        ]
        pa_table = pyarrow.Table.from_arrays(pa_arrays, schema=schema)
        self._register_updated_min_max(table, pa_table)
        # warning: try not to insert duplicate candles, duplicates will be deduplicated later on anyway
        table.append(pa_table)
        # note: alternative upsert syntax could prevent duplicates but is really slow and silentlycrashes the process 
        # when used with a few thousand rows
        # table.upsert(pa_table, join_cols=["timestamp", "exchange_internal_name", "symbol", "time_frame"])
        self._get_logger().info(
            f"Successfully inserted {len(rows)} rows into "
            f"{TableNames.OHLCV_HISTORY.value} for {pa_table['exchange_internal_name'][0]}:{pa_table['symbol'][0]}:{pa_table['time_frame'][0]}"
        )

    @staticmethod
    def get_formatted_time(timestamp: float) -> str:
        return datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        ).isoformat(sep='T').replace("+00:00", "")

    @staticmethod
    def _format_ohlcvs(ohlcvs_table: pyarrow.Table, extended: bool) -> list[list[typing.Union[float, str]]]:
        # ohlcv are fetched in "random" order, sort them before switching to python objects
        batches = ohlcvs_table.sort_by([("timestamp", "ascending")]).to_batches()
        ohlcvs = [
            # time frame
            # symbol
            # then uses PriceIndexes order
            # IND_PRICE_TIME = 0
            # IND_PRICE_OPEN = 1
            # IND_PRICE_HIGH = 2
            # IND_PRICE_LOW = 3
            # IND_PRICE_CLOSE = 4
            # IND_PRICE_VOL = 5
            [tf, s, history_backend_util.get_utc_timestamp_from_datetime(t), o, h, l, c, v]
            for batch in batches
            if (batch_dict := batch.to_pydict())
            for tf, s, t, o, h, l, c, v in zip(
                batch_dict['time_frame'], batch_dict['symbol'], batch_dict['timestamp'], batch_dict['open'], batch_dict['high'], batch_dict['low'], batch_dict['close'], batch_dict['volume']
            )
        ] if extended else [
            # uses PriceIndexes order
            # IND_PRICE_TIME = 0
            # IND_PRICE_OPEN = 1
            # IND_PRICE_HIGH = 2
            # IND_PRICE_LOW = 3
            # IND_PRICE_CLOSE = 4
            # IND_PRICE_VOL = 5
            [history_backend_util.get_utc_timestamp_from_datetime(t), o, h, l, c, v]
            for batch in batches
            if (batch_dict := batch.to_pydict())
            for t, o, h, l, c, v in zip(
                batch_dict['timestamp'], batch_dict['open'], batch_dict['high'], batch_dict['low'], batch_dict['close'], batch_dict['volume']
            )
        ]
        return ohlcvs
    
    def _load_catalog(self) -> pyiceberg.catalog.Catalog:
        self.namespace = constants.ICEBERG_CATALOG_NAMESPACE
        catalog = pyiceberg.catalog.load_catalog(constants.ICEBERG_CATALOG_NAME, **self._get_catalog_properties())
        if constants.CREATE_ICEBERG_DB_IF_MISSING:
            self._ensure_namespace(catalog)
        self._get_logger().info(f"PyIceberg catalog '{constants.ICEBERG_CATALOG_NAME}' successfully loaded")
        return catalog

    def drop_table(self, table_name: str) -> None:
        self.catalog.purge_table(f"{self.namespace}.{table_name}")
        self._get_logger().info(f"Table {table_name} deleted successfully")

    async def resynchronize_min_max_per_symbol_per_time_frame_per_exchange_metadata(self, exchanges: list[str]):
        # Maintenance operation
        # To use if db metadata got deleted or need to be recreated from scratch for any reason.
        # Warning: will sequentially scan the olhcv history tables for all exchanges, requires a lot of ram 
        # (usually around 1 GB)
        self._updated_min_max_per_symbol_per_time_frame_per_exchange = await self._run_in_executor(
            self._sync_get_min_max_per_symbol_per_time_frame_per_exchange_metadata,
            exchanges
        )

    def _sync_get_min_max_per_symbol_per_time_frame_per_exchange_metadata(
        self, exchanges: list[str]
    ) -> dict[str, dict[str, dict[str, tuple[float, float]]]]:
        updated_metadata = {}
        global_t0 = time.time()
        table = self._get_or_create_table(TableNames.OHLCV_HISTORY)
        selected_fields = ("timestamp", "exchange_internal_name", "symbol", "time_frame")
        for exchange in exchanges:
            t0 = time.time()
            self._update_min_max_per_symbol_per_time_frame_per_exchange_for_table(
                self._scan_all_candles_for_exchange(table, exchange, selected_fields).to_arrow(), updated_metadata
            )
            used_ram = os_util.get_cpu_and_ram_usage(0)[3]
            self._get_logger().info(f"Updated metadata for {exchange} in {time.time() - t0} seconds, using {used_ram} GB of RAM")
        self._get_logger().info(
            f"Total time to update metadata for {len(exchanges)} exchanges: {exchange} = {len(exchanges)}: {time.time() - global_t0} seconds"
        )
        return updated_metadata

    async def _update_metadata(self) -> None:
        await self._run_in_executor(self._sync_update_metadata)

    def _get_snapshot_id(self, table: pyiceberg.table.Table) -> int:
        return table.current_snapshot().snapshot_id if table.current_snapshot() else 0

    def _sync_update_metadata(self) -> None:
        ohlcv_table = self._get_or_create_table(TableNames.OHLCV_HISTORY)
        # Get current snapshot ID from the table
        current_snapshot_id = self._get_snapshot_id(ohlcv_table)

        blob_metadata_list = self._create_blob_metadata_list(current_snapshot_id, ohlcv_table)
        
        # Calculate total file size (approximate)
        total_data_size = sum(len(json.dumps(blob.properties or {})) for blob in blob_metadata_list)
        
        # Create a unique statistics file path
        statistics_path = f"{ohlcv_table.location()}/statistics/{current_snapshot_id}.json"
        
        # Create the StatisticsFile with the blob_metadata
        # Using field names (Pydantic will map to aliases automatically)
        statistics_file = pyiceberg.table.statistics.StatisticsFile(
            snapshot_id=current_snapshot_id,  # type: ignore
            statistics_path=statistics_path,  # type: ignore
            file_size_in_bytes=total_data_size,  # type: ignore   # warning: required to store all metadata blobs
            file_footer_size_in_bytes=total_data_size,  # type: ignore   # warning: required to store all metadata blobs
            key_metadata=None,  # type: ignore
            blob_metadata=blob_metadata_list,  # type: ignore
        )
        t0 = time.time()
        self._get_logger().info(f"Updating statistics for {ohlcv_table.name()} with {len(blob_metadata_list)} blob metadata")
        self._update_statistics(ohlcv_table, statistics_file)
        self._get_logger().info(
            f"Completed updating statistics for {ohlcv_table.name()} with {len(blob_metadata_list)} "
            f"blob metadata in {round(time.time() - t0, 2)} seconds"
        )

    def _scan_all_candles_for_exchange(self, table: pyiceberg.table.Table, exchange: str, selected_fields: tuple[str]) -> pyiceberg.table.DataScan:
        filter = pyiceberg.expressions.EqualTo("exchange_internal_name", exchange)
        return table.scan(
            row_filter=filter,
            selected_fields=selected_fields,
            case_sensitive=True,
        )

    def _update_statistics(
        self, table: pyiceberg.table.Table, statistics_file: pyiceberg.table.statistics.StatisticsFile
    ) -> None:
        # only keep the last _MAX_STATISTICS_FILES most recent statistics files to avoid growing metadata size forever
        # -1 as we are also adding a new statistics file
        to_remove_statistics_files = self._get_recent_to_older_statistics_files(table)[(_MAX_STATISTICS_FILES - 1):]
        # each update can only process 1 operation
        for to_delete_statistics_file in to_remove_statistics_files:
            with table.update_statistics() as update:
                self._get_logger().info(
                    f"Clearing statistics for {table.name()} with snapshot id: {to_delete_statistics_file.snapshot_id} to free up space."
                )
                update.remove_statistics(snapshot_id=to_delete_statistics_file.snapshot_id)
        with table.update_statistics() as update:
            self._get_logger().info(
                f"Updating statistics for {table.name()} with snapshot id: {statistics_file.snapshot_id}"
            )
            update.set_statistics(statistics_file=statistics_file)

    def _get_latest_statistics_file_range_metadata(
        self, table: pyiceberg.table.Table
    ) -> pyiceberg.table.statistics.BlobMetadata:
        range_metadata = None
        for metadata in self._get_latest_statistics_file(table).blob_metadata:
            if version := metadata.properties.get(_MetadataIdentifiers.VERSION.value):
                # ensure version compatibility
                if version == _METADATA_VERSION:
                    # version is compatible
                    pass
                else:
                    raise ValueError(
                        f"Latest statistics file version {version} is not compatible with current version {_METADATA_VERSION}"
                    )
            else:
                range_metadata = metadata
        if range_metadata is None:
            raise ValueError(
                f"No range metadata found for table {table.name()}"
            )
        return range_metadata

    def _get_latest_statistics_file(
        self, table: pyiceberg.table.Table
    ) -> pyiceberg.table.statistics.StatisticsFile:
        return self._get_recent_to_older_statistics_files(table)[0]

    def _get_recent_to_older_statistics_files(
        self, table: pyiceberg.table.Table
    ) -> list[pyiceberg.table.statistics.StatisticsFile]:
        return sorted(
            table.metadata.statistics, 
            key=lambda x: -self._get_statistic_file_created_at(x)
        )

    def _get_statistic_file_created_at(
        self, statistics_file: pyiceberg.table.statistics.StatisticsFile
    ) -> float:
        for blob_metadata in statistics_file.blob_metadata:
            if updated_at := blob_metadata.properties.get(_MetadataIdentifiers.UPDATED_AT.value):
                return float(updated_at)
        return 0
    
    def _create_blob_metadata_list(
        self, current_snapshot_id: int, ohlcv_table: pyiceberg.table.Table
    ) -> list[pyiceberg.table.statistics.BlobMetadata]:
        current_min_max_per_symbol_per_time_frame_per_exchange = self._parse_min_max_per_symbol_per_time_frame_per_exchange(
            ohlcv_table
        )
        updated_min_max = {
            # keep previous min max for exchanges that were not updated, replace others
            **current_min_max_per_symbol_per_time_frame_per_exchange, 
            **(self._updated_min_max_per_symbol_per_time_frame_per_exchange or {})
        }
        # Create BlobMetadata objects for all exchange/symbol/timeframe combinations
        updated_properties = {
            f"{exchange}{_METADATA_SEPARATOR}{symbol}{_METADATA_SEPARATOR}{time_frame}": 
                f"{min_timestamp}{_METADATA_SEPARATOR}{max_timestamp}"
            for exchange, symbol_data in updated_min_max.items()
            for symbol, time_frame_data in symbol_data.items()
            for time_frame, (min_timestamp, max_timestamp) in time_frame_data.items()
        }
        
        # Get field IDs from the table schema for timestamp field (field ID 1)
        timestamp_field_id = 1  # Based on the schema definition in _get_ohlcv_schema()
        blob_metadata_list = [
            pyiceberg.table.statistics.BlobMetadata(
                # actual data
                type="apache-datasketches-theta-v1",
                snapshot_id=current_snapshot_id,  # type: ignore
                sequence_number=0,  # type: ignore
                fields=[timestamp_field_id],
                properties=updated_properties
            ),
            pyiceberg.table.statistics.BlobMetadata(
                # to keep track of the latest update in case snapshot id is not enough
                type="apache-datasketches-theta-v1",
                snapshot_id=current_snapshot_id,  # type: ignore
                sequence_number=0,  # type: ignore
                fields=[timestamp_field_id],
                properties={
                    _MetadataIdentifiers.UPDATED_AT.value: str(int(time.time())),
                    _MetadataIdentifiers.VERSION.value: _METADATA_VERSION,
                }
            ),
        ]
        return blob_metadata_list

    def _parse_min_max_per_symbol_per_time_frame_per_exchange(
        self, ohlcv_table: pyiceberg.table.Table
    ) -> dict[str, dict[str, dict[str, tuple[float, float]]]]:
        try:
            properties = self._get_latest_statistics_file_range_metadata(ohlcv_table).properties
        except ValueError:
            # should never happen, raise if it does
            raise
        except IndexError:
            # no metadata found
            return {}
        min_max_per_symbol_per_time_frame_per_exchange = {}
        for key, values in properties.items():
            exchange, symbol, time_frame = key.split(_METADATA_SEPARATOR)
            if exchange not in min_max_per_symbol_per_time_frame_per_exchange:
                min_max_per_symbol_per_time_frame_per_exchange[exchange] = {}
            if symbol not in min_max_per_symbol_per_time_frame_per_exchange[exchange]:
                min_max_per_symbol_per_time_frame_per_exchange[exchange][symbol] = {}
            min_max_per_symbol_per_time_frame_per_exchange[exchange][symbol][time_frame] = tuple(map(float, values.split(_METADATA_SEPARATOR)))
        return min_max_per_symbol_per_time_frame_per_exchange

    def _register_updated_min_max(self, table: pyiceberg.table.Table, update_table: pyarrow.Table) -> None:
        if self._updated_min_max_per_symbol_per_time_frame_per_exchange is None:
            self._updated_min_max_per_symbol_per_time_frame_per_exchange = self._parse_min_max_per_symbol_per_time_frame_per_exchange(
                table
            )
        self._update_min_max_per_symbol_per_time_frame_per_exchange_for_table(
            update_table, self._updated_min_max_per_symbol_per_time_frame_per_exchange
        )

    @staticmethod
    def _update_min_max_per_symbol_per_time_frame_per_exchange_for_table(
        update_table: pyarrow.Table, 
        current_min_max_per_symbol_per_time_frame_per_exchange: dict[str, dict[str, dict[str, tuple[float, float]]]]
    ):
        grouped_result = update_table.group_by(
            ["exchange_internal_name", "symbol", "time_frame"]
        ).aggregate([
            ("timestamp", "hash_min"),
            ("timestamp", "hash_max")
        ])

        update_min_max_per_symbol_per_time_frame_per_exchange = {}
        for exchange, symbol, time_frame, ts_min, ts_max in zip(
            grouped_result['exchange_internal_name'], grouped_result['symbol'], grouped_result['time_frame'], grouped_result['timestamp_min'], grouped_result['timestamp_max']
        ):
            py_exchange = exchange.as_py() # type: ignore
            py_symbol = symbol.as_py() # type: ignore
            py_time_frame = time_frame.as_py() # type: ignore
            if py_exchange not in update_min_max_per_symbol_per_time_frame_per_exchange:
                update_min_max_per_symbol_per_time_frame_per_exchange[py_exchange] = {}
            if py_symbol not in update_min_max_per_symbol_per_time_frame_per_exchange[py_exchange]:
                update_min_max_per_symbol_per_time_frame_per_exchange[py_exchange][py_symbol] = {}
            update_min_max_per_symbol_per_time_frame_per_exchange[py_exchange][py_symbol][py_time_frame] = (
                history_backend_util.get_utc_timestamp_from_datetime(ts_min.as_py()), 
                history_backend_util.get_utc_timestamp_from_datetime(ts_max.as_py())
            )
        # save updated min max per symbol per time frame per exchange in current_min_max_per_symbol_per_time_frame_per_exchange
        for exchange, symbol_data in update_min_max_per_symbol_per_time_frame_per_exchange.items():
            if exchange not in current_min_max_per_symbol_per_time_frame_per_exchange:
                current_min_max_per_symbol_per_time_frame_per_exchange[exchange] = symbol_data
            else:
                current_exchange_data = current_min_max_per_symbol_per_time_frame_per_exchange[exchange]
                for symbol, time_frame_data in symbol_data.items():
                    if symbol not in current_exchange_data:
                        current_exchange_data[symbol] = time_frame_data
                    else:
                        current_symbol_data = current_exchange_data[symbol]
                        for time_frame, (min_timestamp, max_timestamp) in time_frame_data.items():
                            if time_frame not in current_symbol_data:
                                current_symbol_data[time_frame] = (min_timestamp, max_timestamp)
                            else:
                                min_ts = min(min_timestamp, current_symbol_data[time_frame][0])
                                max_ts = max(max_timestamp, current_symbol_data[time_frame][1])
                                current_symbol_data[time_frame] = (min_ts, max_ts)
    
    def _get_or_create_table(self, table_name: TableNames) -> pyiceberg.table.Table:
        try:
            return self.catalog.load_table(f"{self.namespace}.{table_name.value}")
        except pyiceberg.exceptions.NoSuchTableError:
            table_by_ns = {ns: self.catalog.list_tables(ns) for ns in self.catalog.list_namespaces()}
            self._get_logger().info(
                f"Table {table_name.value} does not exist in {self.namespace} namespace. Tables by namespace: {table_by_ns}"
            )
            if constants.CREATE_ICEBERG_DB_IF_MISSING:
                self.catalog.create_table(
                    identifier=f"{self.namespace}.{table_name.value}",
                    schema=self._get_schema_for_table(table_name),
                    sort_order=pyiceberg.table.sorting.SortOrder(
                        pyiceberg.table.sorting.SortField(
                            source_id=1,
                            direction=pyiceberg.table.sorting.SortDirection.DESC, # warning: not applied in selects
                        )
                    )
                )
                self._get_logger().info(f"Table {table_name.value} created successfully")
                return self.catalog.load_table(f"{self.namespace}.{table_name.value}")
            raise
    
    def _ensure_namespace(self, catalog: pyiceberg.catalog.Catalog):
        # Check if namespace exists, create if not
        namespaces = [ns[0] for ns in catalog.list_namespaces()]
        if self.namespace not in namespaces:
            catalog.create_namespace(self.namespace)
            self._get_logger().info(f"Namespace {self.namespace} created")

    @staticmethod
    def _get_catalog_properties() -> dict:
        catalog_properties = {
            "type": "rest",
            "uri": constants.ICEBERG_CATALOG_URI,
            "warehouse": constants.ICEBERG_CATALOG_WAREHOUSE,
            "py-io-impl": "pyiceberg.io.pyarrow.PyArrowFileIO",
            "s3.force-virtual-addressing": False,
        }
        if constants.ICEBERG_CATALOG_TOKEN:
            catalog_properties["token"] = constants.ICEBERG_CATALOG_TOKEN
        if constants.ICEBERG_S3_ACCESS_KEY and constants.ICEBERG_S3_SECRET_KEY:
            catalog_properties.update({
                "s3.access-key-id": constants.ICEBERG_S3_ACCESS_KEY,
                "s3.secret-access-key": constants.ICEBERG_S3_SECRET_KEY,
                "s3.region": constants.ICEBERG_S3_REGION,
            })
            
            if constants.ICEBERG_S3_ENDPOINT:
                catalog_properties["s3.endpoint"] = constants.ICEBERG_S3_ENDPOINT
        return catalog_properties

    @staticmethod
    def _get_schema_for_table(table_name: TableNames) -> typing.Union[pyarrow.Schema, pyiceberg.schema.Schema]:
        if table_name is TableNames.OHLCV_HISTORY:
            return IcebergHistoricalBackendClient._get_ohlcv_schema()
        raise ValueError(f"No schema found for table '{table_name}'. Available schemas: {list(TableNames)}")

    @staticmethod
    def _get_ohlcv_schema() -> pyiceberg.schema.Schema:
        """Schema for OHLCV data"""
        return pyiceberg.schema.Schema(
            pyiceberg.types.NestedField(1, "timestamp", pyiceberg.types.TimestampType(), required=True),
            pyiceberg.types.NestedField(2, "exchange_internal_name", pyiceberg.types.StringType(), required=True),
            pyiceberg.types.NestedField(3, "symbol", pyiceberg.types.StringType(), required=True),
            pyiceberg.types.NestedField(4, "time_frame", pyiceberg.types.StringType(), required=True),
            pyiceberg.types.NestedField(5, "open", pyiceberg.types.DoubleType(), required=True),
            pyiceberg.types.NestedField(6, "high", pyiceberg.types.DoubleType(), required=True),
            pyiceberg.types.NestedField(7, "low", pyiceberg.types.DoubleType(), required=True),
            pyiceberg.types.NestedField(8, "close", pyiceberg.types.DoubleType(), required=True),
            pyiceberg.types.NestedField(9, "volume", pyiceberg.types.DoubleType(), required=True),
        )
    @staticmethod
    def _pyarrow_get_ohlcv_schema() -> pyarrow.schema:
        """Schema for OHLCV data"""
        return pyarrow.schema([
            pyarrow.field("timestamp", pyarrow.timestamp("us"), False),  # Adjust precision as needed (e.g., "ms" for milliseconds)
            pyarrow.field("exchange_internal_name", pyarrow.string(), False),
            pyarrow.field("symbol", pyarrow.string(), False),
            pyarrow.field("time_frame", pyarrow.string(), False),
            pyarrow.field("open", pyarrow.float64(), False),
            pyarrow.field("high", pyarrow.float64(), False),
            pyarrow.field("low", pyarrow.float64(), False),
            pyarrow.field("close", pyarrow.float64(), False),
            pyarrow.field("volume", pyarrow.float64(), False),
        ])

    @classmethod
    def _get_logger(cls):
        return commons_logging.get_logger(cls.__name__)

    def _has_metadata_to_update(self) -> bool:
        return bool(self._updated_min_max_per_symbol_per_time_frame_per_exchange)
