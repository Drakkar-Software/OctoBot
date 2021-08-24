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
import pytest
import time

import octobot.community as community


ERROR_TITLE = "An error happened"
ERROR_METRICS_ID = "1254xyz"
ERROR_TIME = time.time()
UPLOADER_URL = "http://upload_url"


@pytest.fixture
def basic_error():
    return community.Error(
        None,
        ERROR_TITLE,
        ERROR_TIME,
        ERROR_METRICS_ID
    )


@pytest.fixture
def exception_error():
    # generated exception with traceback
    return community.Error(
        _get_exception(),
        ERROR_TITLE,
        ERROR_TIME,
        ERROR_METRICS_ID
    )


@pytest.fixture
def error_uploader():
    return community.ErrorsUploader(UPLOADER_URL)


def _get_exception():
    def fake3():
        1/0

    def fake2():
        fake3()

    def fake_func():
        fake2()
    try:
        fake_func()
    except ZeroDivisionError as err:
        return err
