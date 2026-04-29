#  Drakkar-Software OctoBot-Services
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


class ExchangeWatcher:
    """
    ExchangeWatcher is used as a superclass for elements that require to interact with exchanges.
    register_new_exchange_impl(self, exchange_id) will be called whenever a new exchange is ready.
    Registered exchange ids are stored in self.registered_exchanges_ids
    """
    def __init__(self):
        self.registered_exchanges_ids = set()

    async def register_new_exchange(self, exchange_id):
        try:
            await self.register_new_exchange_impl(exchange_id)
        finally:
            self.registered_exchanges_ids.add(exchange_id)

    async def register_new_exchange_impl(self, exchange_id):
        pass
