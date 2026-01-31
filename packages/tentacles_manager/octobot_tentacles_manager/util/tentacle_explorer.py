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
import os
import os.path as path
import typing

import octobot_commons.logging as logging
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.models as models


_extra_tentacle_data_by_name: dict[str, tuple[models.TentacleType, typing.ClassVar]] = {}


def load_tentacle_with_metadata(tentacle_path: str):
    loaded_tentacles = _parse_all_tentacles(tentacle_path)
    _load_all_metadata(loaded_tentacles)
    return loaded_tentacles


def get_tentacles_from_package(tentacles, package_name: str):
    return [
        tentacle
        for tentacle in tentacles
        if tentacle.origin_package == package_name
    ]


def register_extra_tentacle_data(tentacle_name: str, tentacle_type_path: str, tentacle_class):
    """
    :param tentacle_name: name of the tentacle
    :param tentacle_type_path: path of the tentacle, ex "Trading/mode"
    :param tentacle_class: class of the tentacle
    """
    _extra_tentacle_data_by_name[tentacle_name] = (models.TentacleType(tentacle_type_path), tentacle_class)


def get_tentacle_class_from_extra_tentacles(tentacle_name: str):
    return _extra_tentacle_data_by_name[tentacle_name][1]


def _load_all_metadata(tentacles):
    for tentacle in tentacles:
        try:
            tentacle.sync_initialize()
        except Exception as e:
            logging.get_logger(__name__).error(f"Error when loading {tentacle} ({tentacle.tentacle_path}) metadata: {e}")
            raise e


def _parse_all_tentacles(root: str):
    factory = models.TentacleFactory(root)
    return [
        factory.create_tentacle_from_type(tentacle_entry.name, tentacle_type)
        for tentacle_type in _get_tentacle_types(root)
        for tentacle_entry in os.scandir(path.join(root, tentacle_type.to_path()))
        if not (tentacle_entry.name == constants.PYTHON_INIT_FILE or
                tentacle_entry.name in constants.FOLDERS_BLACK_LIST)
    ] + [
        factory.create_tentacle_from_type(tentacle_name, tentacle_type, [tentacle_name])
        for tentacle_name, (tentacle_type, _) in _extra_tentacle_data_by_name.items()
    ]


def _get_tentacle_types(ref_tentacles_root):
    tentacle_types = []
    if path.isdir(ref_tentacles_root):
        _find_tentacles_type_in_directories(ref_tentacles_root, tentacle_types)
    return tentacle_types


def _find_tentacles_type_in_directories(ref_tentacles_root: os.DirEntry, tentacle_types: list, current_level=1):
    if current_level <= constants.TENTACLE_MAX_SUB_FOLDERS_LEVEL:
        for tentacle_type_entry in os.scandir(ref_tentacles_root):
            if tentacle_type_entry.is_dir():
                _explore_tentacle_dir(tentacle_type_entry, tentacle_types, current_level)


def _explore_tentacle_dir(tentacle_type_entry: os.DirEntry, tentacle_types: list, nesting_level: int):
    # full_tentacle_type_path is the path to the current directory starting from the most global Tentacle type without
    # anything before it:
    # ex: with a at tentacle_dir="downloaded_tentacles/xyz/Backtesting/importers" then
    # full_tentacle_type_path will be "Backtesting/importers"
    full_tentacle_type_path = tentacle_type_entry.path.split(path.sep)[-nesting_level:]
    if not _add_tentacle_type_if_is_valid(tentacle_type_entry, path.join(*full_tentacle_type_path), tentacle_types):
        # no tentacle in this folder, look into nested folders
        _find_tentacles_type_in_directories(tentacle_type_entry, tentacle_types, nesting_level + 1)


def _add_tentacle_type_if_is_valid(tentacle_type_entry: os.DirEntry,
                                   full_tentacle_type_path: str,
                                   tentacle_types: list):
    if _has_tentacle_in_direct_sub_directories(tentacle_type_entry):
        tentacle_types.append(models.TentacleType(full_tentacle_type_path))
        return True
    return False


def _has_tentacle_in_direct_sub_directories(directory_entry: os.DirEntry):
    return any(
        file_entry.name == constants.TENTACLE_METADATA
        for sub_directory_entry in os.scandir(directory_entry)
        if sub_directory_entry.is_dir()
        for file_entry in os.scandir(sub_directory_entry)
    )
