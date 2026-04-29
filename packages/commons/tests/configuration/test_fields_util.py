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
import uuid
import octobot_commons.configuration as configuration


def test_get_password_hash():
    assert len(configuration.get_password_hash("")) == 64
    assert len(configuration.get_password_hash("1")) == 64
    assert len(configuration.get_password_hash("1a")) == 64
    for _ in range(100):
        rand_password = str(uuid.uuid4())
        hashed_password = configuration.get_password_hash(rand_password)
        assert len(hashed_password) == 64
        assert not hashed_password == rand_password
