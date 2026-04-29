# pylint: disable=W0703,R0902
#  Drakkar-Software OctoBot
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
import threading
import tracemalloc
import csv
import gc

import octobot_commons.constants as commons_constants
import octobot_commons.singleton as singleton
import octobot_commons.timestamp_util as timestamp_util
import octobot_commons.logging as logging
import octobot_commons.async_job as async_job
import octobot_commons.os_util as os_util


class SystemResourcesWatcher(singleton.Singleton):
    DEFAULT_WATCHER_INTERVAL = (
        commons_constants.RESOURCES_WATCHER_MINUTES_INTERVAL
        * commons_constants.MINUTE_TO_SECONDS
    )
    CPU_WATCHING_SECONDS = 2

    def __init__(self, dump_resources, watch_ram, output_file, dump_snapshot=False):
        super().__init__()
        self.watcher_job = None
        self.watcher_interval: float = self.DEFAULT_WATCHER_INTERVAL
        self.logger = logging.get_logger(self.__class__.__name__)
        self.watch_ram = watch_ram
        self.dump_resources = dump_resources
        self.output_file = output_file
        self.dump_snapshot = dump_snapshot
        self.snapshot_file = f"{output_file}_snapshot.dump"
        self.initialized_output = False
        self.first_memory_snapshot = None
        self.largest_peak = 0

    def _log_memory(self):
        self.logger.debug("Memory snapshot:")
        # see https://docs.python.org/3/library/tracemalloc.html
        snapshot = tracemalloc.take_snapshot()
        if not self.first_memory_snapshot:
            self.first_memory_snapshot = snapshot

        limit = 20
        top_stats = snapshot.compare_to(self.first_memory_snapshot, "lineno")

        # Summary + changes
        print(f"[ Top {limit} differences ]")
        for stat in top_stats[:limit]:
            print(stat)

        # Top RAM users context
        top_stats = snapshot.statistics("traceback")
        print("Top %s lines" % limit)
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            print(
                "#%s: %s:%s: %.1f KiB"
                % (index, frame.filename, frame.lineno, stat.size / 1024)
            )
            for _line in stat.traceback.format():
                print("    %s" % _line)

        # Other stats
        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
            print("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        print("Total allocated size: %.1f KiB" % (total / 1024))

        latest_size, latest_peak = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()

        # Memory peaks
        self.largest_peak = max(latest_peak, self.largest_peak)
        print(
            f"{latest_size=}, latest_peak={latest_peak/1024} largest_peak={self.largest_peak/1024}"
        )

    def _exec_log_used_resources(self):
        try:
            # trigger garbage collector to get a fresh memory picture
            gc.collect()
            # warning: blocking to monitor CPU usage, to be used in a thread
            cpu, percent_ram, ram, process_ram, virtual_ram, unique_ram = os_util.get_cpu_and_ram_usage(
                self.CPU_WATCHING_SECONDS
            )
            self.logger.debug(
                f"Used system resources: {cpu}% CPU, {ram:,.3f} GB in RAM ({percent_ram}% of total) "
                f"Process memory usage: {unique_ram:,.3f} unique (without shared), {process_ram:,.3f} "
                f"total non-swapped, {virtual_ram:,.3f} total including swap - in GB."
            )
            if self.dump_resources:
                self._dump_resources(cpu, percent_ram, ram, process_ram)
            if self.watch_ram:
                self._log_memory()
            if self.dump_snapshot:
                snapshot = tracemalloc.take_snapshot()
                snapshot.dump(self.snapshot_file)
                self.logger.debug(f"Memory snapshot dumped to {self.snapshot_file}")
        except Exception as err:
            self.logger.exception(err, False)
            self.logger.debug(f"Error when checking system resources: {err}")

    async def _log_used_resources(self):
        threading.Thread(
            target=self._exec_log_used_resources,
            daemon=True,
            name=f"{self.__class__.__name__}-_exec_log_used_resources",
        ).start()

    def _dump_resources(self, cpu, percent_ram, ram, process_ram):
        reset_file = not self.initialized_output
        self.initialized_output = True
        mode = "w" if reset_file else "a"
        row = (
            str(element).replace(".", ",")
            for element in (
                timestamp_util.get_now_time(),
                process_ram,
                cpu,
                percent_ram,
                ram,
            )
        )
        with open(self.output_file, mode, newline="") as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            if reset_file:
                writer.writerow(
                    [
                        "TIME",
                        "PROCESS USED RAM",
                        "% USED CPU",
                        "% USED RAM",
                        "TOTAL USED RAM",
                    ]
                )
            writer.writerow(row)

    async def start(self):
        """
        Synch the clock and start the clock synchronization loop if possible on this system
        """
        self.logger.debug("Starting system resources watcher")
        self.watcher_job = async_job.AsyncJob(
            self._log_used_resources,
            execution_interval_delay=self.watcher_interval,
        )
        await self.watcher_job.run()
        if self.watch_ram or self.dump_snapshot:
            self.logger.debug("RAM watched enabled")
            stored_frames = 5
            tracemalloc.start(stored_frames)

    def stop(self):
        """
        Stop the synchronization loop
        """
        if self.watcher_job is not None and not self.watcher_job.is_stopped():
            self.logger.debug("Stopping system resources watcher")
            self.watcher_job.stop()
        if self.watch_ram or self.dump_snapshot:
            self.logger.debug("Stopping RAM watcher")
            tracemalloc.stop()


async def start_system_resources_watcher(
    dump_resources,
    watch_ram,
    output_file,
    dump_snapshot=False
):
    """
    Start the resources watcher loop
    """
    await SystemResourcesWatcher.instance(
        dump_resources, watch_ram, output_file, dump_snapshot
    ).start()


async def stop_system_resources_watcher():
    """
    Stop the watcher loop
    """
    return SystemResourcesWatcher.instance().stop()


def analyze_dump(filename):
    """
    Analyze a memory snapshot dump file and print the top lines by memory consumption
    """
    try:
        snapshot = tracemalloc.Snapshot.load(filename)
        stats = snapshot.statistics('lineno')
        print("Top 10 lines by memory consumption:")
        for index, stat in enumerate(stats[:10]):
            print(f"#{index+1}: {stat.size / 1024:.2f} KiB in {stat.count} blocks: {stat.traceback}")
    except FileNotFoundError:
        print(f"Error: Dump file '{filename}' not found.")
    except Exception as e:
        print(f"An error occurred while loading or analyzing the snapshot: {e}")

#analyze_dump("system_resources.csv_snapshot.dump")
