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

import pyarrow
import pyiceberg.catalog
import pyiceberg.schema
import pyiceberg.types
import pyiceberg.exceptions
import pyiceberg.expressions
import pyiceberg.table
import pyiceberg.table.sorting

import octobot_commons.logging as commons_logging
import octobot_commons.enums as commons_enums
import octobot.constants as constants
import octobot.community.history_backend.historical_backend_client as historical_backend_client
import octobot.community.history_backend.util as history_backend_util


# avoid "Loaded FileIO: pyiceberg.io.pyarrow.PyArrowFileIO" info logs
logging.getLogger("pyiceberg.io").setLevel(logging.WARNING)


class TableNames(enum.Enum):
    OHLCV_HISTORY = constants.ICEBERG_OHLCV_HISTORY_TABLE


# pyiceberg itself uses a thread pool so each thread will create children threads, limit the number of "master" threads
_MAX_EXECUTOR_WORKERS = min(4, (os.cpu_count() or 1)) # use a max of 4 workers


class IcebergHistoricalBackendClient(historical_backend_client.HistoricalBackendClient):

    def __init__(self):
        self.namespace: typing.Optional[str] = None
        self.catalog: pyiceberg.catalog.Catalog = None # type: ignore
        self._executor: typing.Optional[concurrent.futures.ThreadPoolExecutor] = None # only availble when client is open
        
    async def open(self):
        try:
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=_MAX_EXECUTOR_WORKERS)
            self.catalog = self._load_catalog()
        except Exception as err:
            message = f"Error when connecting to Iceberg server, {err.__class__.__name__}: {err}"
            self.get_logger().exception(err, True, message)
            raise err.__class__(message) from err

    async def close(self):
        if self._executor is not None:
            self._executor.shutdown()
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
            exchange, symbol, time_frame, first_open_time, last_open_time
        )

    def _sync_fetch_candles_history(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames,
        first_open_time: float,
        last_open_time: float
    ) -> list[list[float]]:
        table = self.get_or_create_table(TableNames.OHLCV_HISTORY)
        filter = pyiceberg.expressions.And(
            pyiceberg.expressions.EqualTo("time_frame", time_frame.value),
            pyiceberg.expressions.EqualTo("exchange_internal_name", exchange),
            pyiceberg.expressions.EqualTo("symbol", symbol),
            pyiceberg.expressions.GreaterThanOrEqual("timestamp", self._get_formatted_time(first_open_time)),
            pyiceberg.expressions.LessThanOrEqual("timestamp", self._get_formatted_time(last_open_time))
        )
        result = table.scan(
            row_filter=filter,
            selected_fields=("timestamp", "open", "high", "low", "close", "volume"),
            case_sensitive=True,
        )

        return self._format_ohlcvs(result.to_arrow())

    async def fetch_candles_history_range(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames
    ) -> tuple[float, float]:
        return await self._run_in_executor(
            self._sync_fetch_candles_history_range,
            exchange, symbol, time_frame
        )

    def _sync_fetch_candles_history_range(
        self,
        exchange: str,
        symbol: str,
        time_frame: commons_enums.TimeFrames
    ) -> tuple[float, float]:
        table = self.get_or_create_table(TableNames.OHLCV_HISTORY)
        filter = pyiceberg.expressions.And(
            pyiceberg.expressions.EqualTo("time_frame", time_frame.value),
            pyiceberg.expressions.EqualTo("exchange_internal_name", exchange),
            pyiceberg.expressions.EqualTo("symbol", symbol),
        )
        result = table.scan(
            row_filter=filter,
            selected_fields=("timestamp", ),
            case_sensitive=True,
        )
        res = result.to_arrow()
        # impossible to select the min and max timestamp from the query, 
        # select all and parse the minimum instead
        batches = list(res.to_batches(max_chunksize=10))
        if batches:
            min_ts = batches[0].to_pydict()['timestamp'][0]
            max_ts = batches[-1].to_pydict()['timestamp'][-1]
            return (
                history_backend_util.get_utc_timestamp_from_datetime(min_ts),
                history_backend_util.get_utc_timestamp_from_datetime(max_ts)
            )
        return 0, 0

    async def fetch_all_candles_for_exchange(self, exchange: str) -> list[list[float]]:
        return await self._run_in_executor(
            self._sync_fetch_all_candles_for_exchange,
            exchange
        )

    def _sync_fetch_all_candles_for_exchange(self, exchange: str) -> list[list[float]]:
        table = self.get_or_create_table(TableNames.OHLCV_HISTORY)
        filter = pyiceberg.expressions.EqualTo("exchange_internal_name", exchange)
        result = table.scan(
            row_filter=filter,
            selected_fields=("timestamp", "symbol", "time_frame", "open", "high", "low", "close", "volume"),
            case_sensitive=True,
        )
        ohlcvs = [
            # convert table into list of candles
            [history_backend_util.get_utc_timestamp_from_datetime(t), exchange, s, tf, o, h, l, c, v]
            for batch in result.to_arrow().to_batches()
            if (batch_dict := batch.to_pydict())
            for t, s, tf, o, h, l, c, v in zip(
                batch_dict['timestamp'], batch_dict['symbol'], batch_dict['time_frame'], batch_dict['open'], batch_dict['high'], batch_dict['low'], batch_dict['close'], batch_dict['volume']
            )
        ]
        return ohlcvs

    async def insert_candles_history(self, rows: list, column_names: list) -> None:
        await self._run_in_executor(
            self._sync_insert_candles_history,
            rows, column_names
        )

    def _sync_insert_candles_history(self, rows: list, column_names: list) -> None:
        if not rows:
            return
        schema = self._pyarrow_get_ohlcv_schema()
        table = self.get_or_create_table(TableNames.OHLCV_HISTORY)
        timestamp_fields = [name for name in column_names if isinstance(schema.field(name).type, pyarrow.TimestampType)]
        pa_arrays = [
            pyarrow.array([
                self._get_formatted_time(row[i]) if name in timestamp_fields else row[i]
                for row in rows
            ]) 
            for i, name in enumerate(column_names)
        ]
        pa_table = pyarrow.Table.from_arrays(pa_arrays, schema=schema)
        # warning: try not to insert duplicate candles, duplicates will be deduplicated later on anyway
        table.append(pa_table)
        # note: alternative upsert syntax could prevent duplicates but is really slow and silentlycrashes the process 
        # when used with a few thousand rows
        # table.upsert(pa_table, join_cols=["timestamp", "exchange_internal_name", "symbol", "time_frame"])
        self.get_logger().info(
            f"Successfully inserted {len(rows)} rows into "
            f"{TableNames.OHLCV_HISTORY.value} for {pa_table['exchange_internal_name'][0]}:{pa_table['symbol'][0]}:{pa_table['time_frame'][0]}"
        )

    @staticmethod
    def _get_formatted_time(timestamp: float) -> str:
        return datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        ).isoformat(sep='T').replace("+00:00", "")

    @staticmethod
    def _format_ohlcvs(ohlcvs_table: pyarrow.Table) -> list[list[float]]:
        # uses PriceIndexes order
        # IND_PRICE_TIME = 0
        # IND_PRICE_OPEN = 1
        # IND_PRICE_HIGH = 2
        # IND_PRICE_LOW = 3
        # IND_PRICE_CLOSE = 4
        # IND_PRICE_VOL = 5
        ohlcvs = [
            # convert table into list of candles
            [history_backend_util.get_utc_timestamp_from_datetime(t), o, h, l, c, v]
            for batch in ohlcvs_table.to_batches()
            if (batch_dict := batch.to_pydict())
            for t, o, h, l, c, v in zip(
                batch_dict['timestamp'], batch_dict['open'], batch_dict['high'], batch_dict['low'], batch_dict['close'], batch_dict['volume']
            )
        ]
        # ensure no duplicates as they can happen due to no unicity constraint
        ohlcvs = history_backend_util.deduplicate(ohlcvs, 0)
        return ohlcvs
    
    def _load_catalog(self) -> pyiceberg.catalog.Catalog:
        self.namespace = constants.ICEBERG_CATALOG_NAMESPACE
        catalog = pyiceberg.catalog.load_catalog(constants.ICEBERG_CATALOG_NAME, **self._get_catalog_properties())
        if constants.CREATE_ICEBERG_DB_IF_MISSING:
            self._ensure_namespace(catalog)
        self.get_logger().info(f"PyIceberg catalog '{constants.ICEBERG_CATALOG_NAME}' initialized successfully")
        return catalog
    
    def get_or_create_table(self, table_name: TableNames) -> pyiceberg.table.Table:
        try:
            return self.catalog.load_table(f"{self.namespace}.{table_name.value}")
        except pyiceberg.exceptions.NoSuchTableError:
            table_by_ns = {ns: self.catalog.list_tables(ns) for ns in self.catalog.list_namespaces()}
            self.get_logger().info(
                f"Table {table_name.value} does not exist in {self.namespace} namespace. Tables by namespace: {table_by_ns}"
            )
            if constants.CREATE_ICEBERG_DB_IF_MISSING:
                self.catalog.create_table(
                    identifier=f"{self.namespace}.{table_name.value}",
                    schema=self._get_schema_for_table(table_name),
                    sort_order=pyiceberg.table.sorting.SortOrder(
                        pyiceberg.table.sorting.SortField(
                            source_id=1,
                            direction=pyiceberg.table.sorting.SortDirection.ASC,
                        )
                    )
                )
                self.get_logger().info(f"Table {table_name.value} created successfully")
                return self.catalog.load_table(f"{self.namespace}.{table_name.value}")
            raise
    
    def _ensure_namespace(self, catalog: pyiceberg.catalog.Catalog):
        # Check if namespace exists, create if not
        namespaces = [ns[0] for ns in catalog.list_namespaces()]
        if self.namespace not in namespaces:
            catalog.create_namespace(self.namespace)
            self.get_logger().info(f"Namespace {self.namespace} created")

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
            pyiceberg.types.NestedField(10, "updated_at", pyiceberg.types.TimestampType(), required=False, initial_default=None),
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
            pyarrow.field("updated_at", pyarrow.timestamp("us"), True),
        ])

    @classmethod
    def get_logger(cls):
        return commons_logging.get_logger(cls.__name__)
