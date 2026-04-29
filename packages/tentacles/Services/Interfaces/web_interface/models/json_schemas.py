#  Drakkar-Software OctoBot-Interfaces
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
import octobot_commons.constants as commons_constants
import octobot_commons.configuration as configuration

import tentacles.Services.Interfaces.web_interface.enums as enums

ASSET = "asset"
VALUE = "value"
HIDDEN_VALUE = "******"

NAME = "name"
API_KEY = "api-key"
API_SECRET = "api-secret"
API_PASSWORD = "api-password"


JSON_PORTFOLIO_SCHEMA = {
    "type": "array",
    "uniqueItems": True,
    "title": "Simulated portfolio",
    "format": "table",
    "items": {
        "type": "object",
        "title": "Asset",
        "properties": {
            ASSET: {
                "title": "Asset",
                "type": "string",
                "enum": [],
            },
            VALUE: {
                "title": "Holding",
                "type": "number",
                "minimum": 0,
            },
        }
    }
}


def get_json_simulated_portfolio(user_config):
    config_portfolio = user_config[commons_constants.CONFIG_SIMULATOR][commons_constants.CONFIG_STARTING_PORTFOLIO]
    return [
        {
            ASSET: asset,
            VALUE: value,
        }
        for asset, value in config_portfolio.items()
    ]


def json_simulated_portfolio_to_config(json_portfolio_config: list[dict]) -> dict:
    return {
        entry[ASSET]: entry[VALUE]
        for entry in json_portfolio_config
    }


JSON_TRADING_SIMULATOR_SCHEMA = {
  "type": "object",
  "title": "Simulated trading configuration",
  "additionalProperties": False,
  "properties": {
    "enabled": {
      "title": "Enable trading simulator When checked, OctoBot will trade with the simulated portfolio",
      "type": "boolean",
      "format": "checkbox",
      "options": {
        "containerAttributes": {
          "class": "mb-3"
        }
      }
    },
    "fees": {
      "type": "object",
      "additionalProperties": False,
      "title": "Trading simulator fees",
      "properties": {
        "maker": {
          "title": "Taker fees: maker trading fee as a % of the trade total cost.",
          "type": "number",
          "minimum": -100,
          "maximum": 100
        },
        "taker": {
          "title": "Taker fees: taker trading fee as a % of the trade total cost.",
          "type": "number",
          "minimum": -100,
          "maximum": 100,
          "step": 0.01
        }
      }
    }
  }
}


def get_json_trading_simulator_config(user_config: dict) -> dict:
    return {
        key: val
        for key, val in user_config[commons_constants.CONFIG_SIMULATOR].items()
        if key in (commons_constants.CONFIG_ENABLED_OPTION, commons_constants.CONFIG_SIMULATOR_FEES)
    }


CONNECTION_TYPE_EXCHANGE_FIELDS = {
    enums.ExchangeConnectionType.API_KEY: {
        "api_key_title": "API key: your API key for this exchange",
        "api_secret_title": "API secret: your API secret for this exchange",
        "api_password_title": "API password: leave empty if not required by exchange",
    },
    enums.ExchangeConnectionType.WALLET: {
        "api_key_title": "Funds Wallet address",
        "api_secret_title": "Funds Wallet private key",
        "api_password_title": "API wallet address : only provide if authenticated with email",
    }
}


def get_json_exchanges_schema(exchanges: list[str], connection_type: enums.ExchangeConnectionType = enums.ExchangeConnectionType.API_KEY) -> dict:
    field_config = CONNECTION_TYPE_EXCHANGE_FIELDS.get(connection_type, CONNECTION_TYPE_EXCHANGE_FIELDS[enums.ExchangeConnectionType.API_KEY])

    return {
        "type": "array",
        "uniqueItems": True,
        "title": "Exchanges",
        "format": "table",
        "additionalProperties": False,
        "items": {
            "type": "object",
            "id": "exchanges",
            "title": "Exchange",
            "additionalProperties": False,
            "properties": {
                NAME: {
                    "title": "Name",
                    "type": "string",
                    "enum": exchanges,
                    "propertyOrder": 1,
                },
                API_KEY: {
                    "title": field_config["api_key_title"],
                    "type": "string",
                    "minLength": 0,
                    "propertyOrder": 2,
                },
                API_SECRET: {
                    "title": field_config["api_secret_title"],
                    "type": "string",
                    "minLength": 0,
                    "propertyOrder": 3,
                },
                API_PASSWORD: {
                    "title": field_config["api_password_title"],
                    "type": "string",
                    "minLength": 0,
                    "propertyOrder": 4,
                },
            }
        }
    }


def get_json_exchange_config(user_config: dict):
    return [
        {
            NAME: name,
            API_KEY: "" if configuration.has_invalid_default_config_value(values.get(commons_constants.CONFIG_EXCHANGE_KEY)) else HIDDEN_VALUE,
            API_SECRET: "" if configuration.has_invalid_default_config_value(values.get(commons_constants.CONFIG_EXCHANGE_SECRET)) else HIDDEN_VALUE,
            API_PASSWORD: "" if configuration.has_invalid_default_config_value(values.get(commons_constants.CONFIG_EXCHANGE_PASSWORD)) else HIDDEN_VALUE,
        }
        for name, values in user_config[commons_constants.CONFIG_EXCHANGES].items()
    ]

def json_exchange_config_to_config(json_exchanges_config: list[dict], enabled: bool):
    return {
        config[NAME]: _get_exchange_config_from_json(config, enabled)
        for config in json_exchanges_config
    }

def _get_exchange_config_from_json(json_exchange_config: dict, enabled: bool) -> dict:
    config = {
        commons_constants.CONFIG_ENABLED_OPTION: enabled,
    }
    for json_key, config_key in (
        (API_KEY, commons_constants.CONFIG_EXCHANGE_KEY),
        (API_SECRET, commons_constants.CONFIG_EXCHANGE_SECRET),
        (API_PASSWORD, commons_constants.CONFIG_EXCHANGE_PASSWORD),
        (API_KEY, commons_constants.CONFIG_EXCHANGE_KEY),
    ):
        json_value = json_exchange_config[json_key]
        if json_value != HIDDEN_VALUE:
            # only add keys if their value is not HIDDEN_VALUE, use commons_constants.EMPTY_VALUE instead of ""
            config[config_key] = json_value or commons_constants.NO_KEY_VALUE
    return config
