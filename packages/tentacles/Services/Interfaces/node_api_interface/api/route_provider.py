#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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

import abc
import enum
import typing

import octobot_commons.tentacles_management.class_inspector as class_inspector

import fastapi


class RouteType(enum.Enum):
    TENTACLES = "tentacles"


def _is_installable_provider_class(
    provider_class: typing.Type[typing.Any],
) -> bool:
    return not class_inspector.is_abstract_using_inspection_and_class_naming(
        provider_class
    )


def _include_router_prefix(route_type: RouteType) -> typing.Optional[str]:
    if route_type == RouteType.TENTACLES:
        return "/tentacles"
    return None


class RouteProvider(abc.ABC):
    """Concrete subclasses must set ``ROUTE_TYPE`` and implement ``get_router``."""

    ROUTE_TYPE: typing.ClassVar[RouteType]

    @abc.abstractmethod
    def get_router(self) -> fastapi.APIRouter:
        raise NotImplementedError


def register_all_provider_routes(api_router: fastapi.APIRouter) -> None:
    for provider_class in class_inspector.get_all_classes_from_parent(RouteProvider):
        if not _is_installable_provider_class(provider_class):
            continue
        route_prefix = _include_router_prefix(provider_class.ROUTE_TYPE)
        if route_prefix is not None:
            api_router.include_router(
                provider_class().get_router(), prefix=route_prefix
            )
        else:
            api_router.include_router(provider_class().get_router())
