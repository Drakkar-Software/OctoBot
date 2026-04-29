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
import typing

import tentacles.Services.Interfaces.web_interface.models.configuration as models_configuration


_PM_SERVICES = [
    "telegram", "web"
]

def save_prediction_market_configuration(
    enabled_exchange: str,
    trading_pair: typing.Optional[str],
    exchange_configurations: list[dict],
    trading_simulator_configuration: dict,
    simulated_portfolio_configuration: list[dict],
    trading_mode_name: str,
    trading_mode_configuration: dict,
) -> None:
    models_configuration.save_distribution_configuration(
        trading_mode_name=trading_mode_name,
        trading_mode_configuration=trading_mode_configuration,
        enabled_exchange=enabled_exchange,
        trading_pair=trading_pair,
        exchange_configurations=exchange_configurations,
        trading_simulator_configuration=trading_simulator_configuration,
        simulated_portfolio_configuration=simulated_portfolio_configuration,
    )


def get_prediction_market_services() -> dict:
    return {
        name: service
        for name, service in models_configuration.get_services_list().items()
        if name in _PM_SERVICES
    }
