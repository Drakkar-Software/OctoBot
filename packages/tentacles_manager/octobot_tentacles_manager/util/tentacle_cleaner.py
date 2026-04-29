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
import shutil

import octobot_tentacles_manager.constants as constants


def remove_unnecessary_files(directory) -> None:
    """
    Remove unnecessary files in directory from
    PYTHON_GENERATED_ELEMENTS and PYTHON_GENERATED_ELEMENTS_EXTENSION list
    :param directory: the directory to clean
    :return: None
    """
    for element in os.scandir(directory):
        element_ext = element.name.split(".")[-1]
        if element.name in constants.PYTHON_GENERATED_ELEMENTS or \
                (element_ext in constants.PYTHON_GENERATED_ELEMENTS_EXTENSION and element.is_file()):
            remove_dir_or_file(element)
        elif element.is_dir():
            remove_unnecessary_files(element)


def remove_dir_or_file(element_path: os.path) -> None:
    """
    Remove an os.path element
    :param element_path: the element to remove
    :return: None
    """
    if element_path.is_dir():
        shutil.rmtree(element_path)
    elif element_path.is_file():
        os.remove(element_path)


def remove_dir_or_file_from_path(element_path: str) -> None:
    """
    Remove an os.path element
    :param element_path: the element path to remove
    :return: None
    """
    if os.path.isdir(element_path):
        shutil.rmtree(element_path)
    elif os.path.isfile(element_path):
        os.remove(element_path)

def remove_non_tentacles_files(directory, logger) -> None:
    """
    Cleanup a directory from non tentacle files
    :param directory: the directory path to clean
    :param logger: the logger to use when an error happened
    :return: None
    """
    for element in os.scandir(directory):
        if element.name not in set(constants.TENTACLES_FOLDERS_ARCH):
            try:
                remove_dir_or_file(element)
            except Exception as e:
                logger.error(f"Error when cleaning up temporary folder: {e}")
