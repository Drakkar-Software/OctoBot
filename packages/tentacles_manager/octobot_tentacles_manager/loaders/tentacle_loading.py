#  Drakkar-Software OctoBot-Tentacles-Manager
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
import os.path as path
import typing

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.models as models
import octobot_tentacles_manager.util as util

# tentacle_data_by_tentacle_class is used to cache tentacles metadata
_tentacle_by_tentacle_class = None
_tentacle_class_by_class_name = {}
_tentacle_documentation_by_class_name = {}


def reload_tentacle_by_tentacle_class(tentacles_path=constants.TENTACLES_PATH):
    global _tentacle_by_tentacle_class
    loaded_tentacles = util.load_tentacle_with_metadata(tentacles_path)
    _tentacle_by_tentacle_class = {
        klass: tentacle
        for tentacle in loaded_tentacles
        for klass in tentacle.tentacle_class_names
    }


def get_tentacle_classes() -> dict:
    return _tentacle_by_tentacle_class


def ensure_tentacles_metadata(tentacles_path) -> None:
    if get_tentacle_classes() is None:
        reload_tentacle_by_tentacle_class(tentacles_path)


def get_resources_path(klass) -> str:
    return path.join(get_tentacle_module_path(klass), constants.TENTACLE_RESOURCES)


def get_tentacle_module_path(klass) -> typing.Optional[str]:
    tentacle = get_tentacle(klass)
    return path.join(tentacle.tentacle_path, tentacle.name) if tentacle else None


def get_tentacles_classes_names_from_tentacle_module(tentacle_module_name) -> list:
    return [
        tentacle_name
        for tentacle_name, tentacle_details in _tentacle_by_tentacle_class.items()
        if tentacle_details.name == tentacle_module_name
    ]


def get_tentacles_classes_names_for_type(tentacle_type) -> list:
    tentacle_names = []
    for tentacle_details in _tentacle_by_tentacle_class.values():
        if tentacle_details.tentacle_type.is_of_type(tentacle_type):
            tentacle_names += tentacle_details.tentacle_class_names
    return tentacle_names


def get_documentation_file_path(klass) -> str:
    return path.join(
        get_resources_path(klass),
        f"{klass if isinstance(klass, str) else klass.get_name()}{constants.DOCUMENTATION_EXT}"
    )


def get_documentation(klass) -> str:
    doc_key = klass if isinstance(klass, str) else klass.get_name()
    try:
        # use documentation content cache as documentation is not supposed to change
        return _tentacle_documentation_by_class_name[doc_key]
    except KeyError:
        doc_file = get_documentation_file_path(klass)
        doc_content = ""
        if path.isfile(doc_file):
            with open(doc_file, "r") as doc_file:
                doc_content = doc_file.read()
        _tentacle_documentation_by_class_name[doc_key] = doc_content
    return doc_content


def get_tentacle(klass) -> typing.Optional[models.Tentacle]:
    try:
        return _tentacle_by_tentacle_class.get(klass if isinstance(klass, str) else klass.get_name(), None)
    except (TypeError, AttributeError):
        raise RuntimeError(f"tentacle have not been initialized, call reload_tentacle_by_tentacle_class "
                           f"fix this issue")


def get_tentacle_class_from_name(tentacle_class_name):
    return _tentacle_class_by_class_name[tentacle_class_name]


def set_tentacle_class_by_name(tentacle_class_name, tentacle_class):
    _tentacle_class_by_class_name[tentacle_class_name] = tentacle_class
