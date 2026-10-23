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

import concurrent.futures as futures

import pytest

import octobot_commons.thread_util as thread_util


def test_stop_thread_pool_executor_waits_for_workers():
    executor = futures.ThreadPoolExecutor(max_workers=1)
    finished = []

    def work():
        finished.append(True)

    executor.submit(work)
    thread_util.stop_thread_pool_executor_non_gracefully(executor)
    assert finished == [True]
    with pytest.raises(RuntimeError):
        executor.submit(work)
