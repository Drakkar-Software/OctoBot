# pylint: disable=W0703,R0902,R0913,R1729
#  Drakkar-Software OctoBot-Commons
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
import asyncio
import time

import octobot_commons.logging as logging_util
import octobot_commons.html_util as html_util


class AsyncJob:
    """
    Async job management
    """

    NO_DELAY = 0.1
    DEPENDENCIES_WAIT_TIMEOUT = 300
    SELF_RUNNING_WAIT_TIMEOUT = 30
    MAXIMUM_ALLOWED_SUCCESSIVE_FAILURES = 1

    def __init__(
        self,
        callback,
        execution_interval_delay=NO_DELAY,
        min_execution_delay=NO_DELAY,
        first_execution_delay=NO_DELAY,
        is_periodic=True,
        enable_multiple_runs=False,
        max_successive_failures=MAXIMUM_ALLOWED_SUCCESSIVE_FAILURES,
    ):
        self.logger = logging_util.get_logger(
            f"{self.__class__.__name__}-{callback.__name__}"
        )
        self.callback = callback
        self.is_started = False
        self.should_stop = False
        self.is_periodic = is_periodic
        self.enable_multiple_runs = enable_multiple_runs
        self.simultaneous_calls = 0
        self.successive_failures = 0

        # Set this attribute to 0 to log on any periodic refresh exception.
        self.max_successive_failures = max_successive_failures

        self.last_execution_time = 0
        self.execution_interval_delay = execution_interval_delay
        self.min_execution_delay = min_execution_delay
        self.first_execution_delay = first_execution_delay

        self.job_dependencies = []
        self.idle_task_event = asyncio.Event()
        self.idle_task_event.set()

        self.job_task = None
        self.job_periodic_task = None

    async def run(
        self,
        force=False,
        wait_for_task_execution=False,
        ignore_dependencies_check=False,
        **kwargs,
    ):
        """
        Run the job if possible
        Reschedule the job in the end
        :param force: When True, force the execution of the job
        :param wait_for_task_execution: When True, await idle_task_event
        :param ignore_dependencies_check: When True, ignore dependencies wait
        """
        if not self.is_started and self.is_periodic:
            self.should_stop = False
            self.job_periodic_task = asyncio.create_task(
                self._run_periodic_task(**kwargs)
            )
        else:
            if self._should_run_job(force=force, ignore_dependencies=True):
                if wait_for_task_execution:
                    await self._run_task_as_soon_as_possible(
                        force=force,
                        ignore_dependencies_check=ignore_dependencies_check,
                        **kwargs,
                    )
                else:
                    self.job_task = asyncio.create_task(
                        self._run_task_as_soon_as_possible(
                            force=force,
                            ignore_dependencies_check=ignore_dependencies_check,
                            **kwargs,
                        )
                    )

    async def _run_periodic_task(self, **kwargs):
        """
        Calls _run() periodically until self.should_stop == True or cancellation
        """
        while not self.should_stop:
            self.is_started = True
            if self.last_execution_time == 0:
                # first execution
                sleep_time = (
                    0
                    if self.first_execution_delay == self.NO_DELAY
                    else self.first_execution_delay
                )
            else:
                # other executions
                sleep_time = (
                    0
                    if time.time() - self.last_execution_time
                    >= self.execution_interval_delay
                    else self.execution_interval_delay
                )
            await asyncio.sleep(sleep_time)
            await self._run_task_as_soon_as_possible(
                error_on_single_failure=False, **kwargs
            )
        self.is_started = False

    async def _run_task_as_soon_as_possible(
        self,
        force=False,
        ignore_dependencies_check=False,
        error_on_single_failure=True,
        **kwargs,
    ):
        """
        Wait until job _run() can be called
        :param force: if True, force job task execution
        """
        if self._should_run_job(force=force):
            await self._run(error_on_single_failure=error_on_single_failure, **kwargs)
        else:
            # wait for job dependencies to stop running
            # and also this job to stop running
            try:
                events_to_wait = []

                # add dependencies event wait_for coroutines
                if not ignore_dependencies_check:
                    events_to_wait += [
                        asyncio.wait_for(
                            dependency.idle_task_event.wait(),
                            self.DEPENDENCIES_WAIT_TIMEOUT,
                        )
                        for dependency in self.job_dependencies
                    ]

                # add self idle event wait_for coroutine
                if not self.enable_multiple_runs:
                    events_to_wait.append(
                        asyncio.wait_for(
                            self.idle_task_event.wait(),
                            self.SELF_RUNNING_WAIT_TIMEOUT,
                        )
                    )

                if events_to_wait:
                    await asyncio.gather(
                        *events_to_wait,
                    )
            except asyncio.TimeoutError:
                self.logger.warning("Job has been timed out")
            finally:
                await self._run(
                    error_on_single_failure=error_on_single_failure, **kwargs
                )

    def is_job_idle(self):
        """
        :return: publicly is_running attribute value
        """
        return self.idle_task_event.is_set()

    def add_job_dependency(self, job):
        """
        Add a new job dependency
        :param job: the new job dependency
        """
        self.job_dependencies.append(job)

    async def _run(self, error_on_single_failure=True, **kwargs):
        """
        Execute the job callback
        Reset the last_execution_time
        """
        # Clear to be able to await the event
        if self.simultaneous_calls == 0:
            self.idle_task_event.clear()
        self.simultaneous_calls += 1
        try:
            await self.callback(**kwargs)
            if self.successive_failures > self.max_successive_failures:
                self.logger.info(
                    f"Job successfully run after {self.successive_failures} failures."
                )
            self.successive_failures = 0
        except Exception as exception:
            self._handle_run_exception(exception, error_on_single_failure)
        finally:
            self.last_execution_time = time.time()
            self.simultaneous_calls -= 1
            if self.simultaneous_calls == 0:
                # Set the event to trigger event waiters
                self.idle_task_event.set()

    def _handle_run_exception(self, exception, error_on_single_failure):
        self.successive_failures += 1
        str_error = html_util.get_html_summary_if_relevant(exception)
        error_message = f"Failed to run job action, exception: {exception.__class__.__name__}: {str_error}"
        if error_on_single_failure:
            self.logger.exception(exception, True, error_message)
        else:
            if self.successive_failures > self.max_successive_failures:
                self.logger.exception(
                    exception,
                    True,
                    f"{error_message} ({self.successive_failures} failures in a row)",
                )
            else:
                self.logger.debug(error_message)
                # always at least print stacktrace in logs
                self.logger.exception(exception, False)

    def _should_run_job(self, force=False, ignore_dependencies=False):
        """
        :param force: If True, enabled job execution even if min_execution_delay > last_execution_time
        :param ignore_dependencies: If True, ignore _are_job_dependencies_running() result
        :return: True if the job is not already running and if _should_run is True
        """
        return (self.is_job_idle() or self.enable_multiple_runs) and (
            (self._are_job_dependencies_idle() or ignore_dependencies)
            and (self._has_enough_time_elapsed() or force)
        )

    def _has_enough_time_elapsed(self):
        """
        :return: True if min_execution_delay < last_execution_time
        """
        return (
            time.time() - self.min_execution_delay > self.last_execution_time
            or self.min_execution_delay == AsyncJob.NO_DELAY
            or self.last_execution_time == 0
        )

    def _are_job_dependencies_idle(self):
        """
        :return: True if a dependent jobs is idle
        """
        return all([job.is_job_idle() for job in self.job_dependencies])

    def is_stopped(self):
        """
        Return True when the AsyncJob has stopped
        """
        return self.should_stop

    def stop(self):
        """
        Stop the job by cancelling the execution task
        """
        self.should_stop = True
        if self.job_task is not None:
            self.job_task.cancel()
            self.job_task = None
        if self.job_periodic_task is not None:
            self.job_periodic_task.cancel()
            self.job_periodic_task = None
        self.is_started = False

    def clear(self):
        """
        Clear job object references and stop it
        """
        self.job_dependencies = []
        self.stop()
