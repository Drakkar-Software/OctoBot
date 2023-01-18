#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
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
    config {
        _id
        profile {
            _id
            name
        }
    }
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
      type
      urls {
        url
      }
    }
    stats {
        _id
        profitability
    }
    user_id
"""


def select_startup_info_query(bot_id) -> (str, dict, str):
    return """
query getBotStartupInfo($bot_id: String) {
  getBotStartupInfo(input: {botId: $bot_id}) {
    subscribedProducts {
        url
    }
    forcedProfileUrl {
        url
    }
  }
}
    """, {"bot_id": bot_id}, "getBotStartupInfo"


def select_subscribed_profiles_query() -> (str, dict, str):
    return """
query getSubscribedProfiles {
  getSubscribedProfiles {
    data {
        url
    }
  }
}
    """, {}, "getSubscribedProfiles"


def select_bots_query() -> (str, dict, str):
    return """
query SelectBots {  
    bots {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {}, "bots"


def select_bot_query(bot_id) -> (str, dict, str):
    return """
query SelectBot($_id: ObjectId) {  
    bot (query: {_id: $_id}) {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {"_id": bot_id},  "bot"


def create_bot_query(is_self_hosted) -> (str, dict, str):
    return """
mutation CreateBot($isSelfHosted: Boolean) {  
    createBot (input: {isSelfHosted: $isSelfHosted}) {
""" + _INNER_BOT_QUERY + """
    }
}
    """, {"isSelfHosted": is_self_hosted}, "createBot"


def create_bot_device_query(bot_id) -> (str, dict, str):
    return """
mutation CreateBotDevice($bot_id: ObjectId) {
  createBotDevice(input: $bot_id) {
    """ + _INNER_BOT_QUERY + """
  }
}
    """, {"bot_id": bot_id}, "createBotDevice"


def update_bot_config_and_stats_query(bot_id, profile_name, profitability) -> (str, dict, str):
    return """
mutation updateOneBot($bot_id: ObjectId, $profile_name: String, $profitability: Decimal) {
  updateOneBot(
    query: {_id: $bot_id}
    set: {config: {profile: {name: $profile_name}}, stats: {profitability: $profitability}}
  ) {
    """ + _INNER_BOT_QUERY + """
  }
}
    """, {"bot_id": bot_id, "profile_name": profile_name, "profitability": str(profitability)}, "updateOneBot"


def update_bot_trades_query(bot_id, trades) -> (str, dict, str):
    return """
mutation updateOneBot($bot_id: ObjectId, $trades: [BotTradeUpdateInput]) {
  updateOneBot(
    query: {_id: $bot_id}
    set: {trades: $trades}
  ) {
    """ + _INNER_BOT_QUERY + """
  }
}
    """, {"bot_id": bot_id, "trades": trades}, "updateOneBot"


def update_bot_portfolio_query(bot_id, current_value, initial_value, unit, content, history) -> (str, dict, str):
    return """
mutation updateOneBot($bot_id: ObjectId, $current_value: Decimal, $initial_value: Decimal, $unit: String, $content: [BotPortfolioContentUpdateInput], $history: [BotPortfolioHistoryUpdateInput]) {
  updateOneBot(
    query: {_id: $bot_id}
    set: {portfolio: {current_value: $current_value, initial_value: $initial_value, unit: $unit, content: $content, history: $history}}
  ) {
    """ + _INNER_BOT_QUERY + """
  }
}
    """, {"bot_id": bot_id, "current_value": str(current_value), "initial_value": str(initial_value),
          "unit": unit, "content": content, "history": history}, "updateOneBot"
