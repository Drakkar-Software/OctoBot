#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2022 Drakkar-Software, All rights reserved.
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


def create_new_device_query() -> (str, dict):
    return """
mutation CreateDevice {
  createDevice {
    _id
    name
    user_id
    uuid
  }
}
    """, {}


def select_device(device_id) -> (str, dict):
    return """
query SelectDeviceUUID($_id: ObjectId) {
  device(query: {_id: $_id}) {
    _id
    uuid
    name
  }
}
    """, {"_id": device_id}


def select_devices() -> (str, dict):
    return """
query SelectDevices {
  devices {
    _id
    uuid
    name
  }
}
    """, {}
