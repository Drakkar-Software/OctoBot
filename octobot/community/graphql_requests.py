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


_INNER_BOT_QUERY = """
    _id
    name
    device {
      _id
      host
      name
      region
      uuid
    }
    deployment {
      _id
      host
      region
      status
      subscription_id
      type
      url
      uuid
    }
    user_id
"""


def select_bots_query() -> (str, dict):
    return """
query SelectBots {  
    bots {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {}


def select_bot_query(bot_id) -> (str, dict):
    return """
query SelectBot($_id: ObjectId) {  
    bot (query: {_id: $_id}) {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {"_id": bot_id}


def create_bot_query(is_self_hosted) -> (str, dict):
    return """
mutation CreateBot($isSelfHosted: Boolean) {  
    createBot (input: {isSelfHosted: $isSelfHosted}) {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {"_id": is_self_hosted}


def create_bot_device_query(bot_id) -> (str, dict):
    return """
mutation CreateBotDevice($bot_id: ObjectId) {
  createBotDevice(input: $bot_id) {
    """ + _INNER_BOT_QUERY + """
  }
}
    """, {"bot_id": bot_id}
