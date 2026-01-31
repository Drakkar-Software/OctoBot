# pylint: disable=W0718
#  Drakkar-Software OctoBot-Commons
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
import json
import os.path
import shutil
import octobot_commons.logging
import octobot_commons.constants

try:
    import jsonschema
except ImportError:
    if octobot_commons.constants.USE_MINIMAL_LIBS:
        # mock jsonschema imports
        class JsonschemaImportMock:
            def validate(
                self, instance, schema
            ):  # pylint: disable=missing-function-docstring
                raise ImportError("jsonschema not installed")

        jsonschema = JsonschemaImportMock()
    else:
        raise


LOGGER_NAME = "json_util"


def validate(config, schema_file) -> None:
    """
    Validate a config file, raise upon validation error
    :param config: the config
    :param schema_file: the config schema
    :return: None
    """
    with open(schema_file) as json_schema:
        loaded_schema = json.load(json_schema)
    jsonschema.validate(instance=config, schema=loaded_schema)


def has_same_content(file_path: str, expected_content: dict) -> bool:
    """
    :return: True if the content of the parsed json file at file_path equals the given expected_content
    """
    if os.path.isfile(file_path):
        content = read_file(file_path, raise_errors=False)
        return content == expected_content
    return False


def read_file(
    file_path: str,
    raise_errors: bool = True,
    on_error_value: dict = None,
    open_mode="r",
) -> dict:
    """
    Read a load the given file with json.load()
    :param file_path: file to read
    :param raise_errors: when True will forward errors. Will just log errors otherwise
    :param on_error_value: return this value when raise_errors is False and an error occurs
    :param open_mode: the file open mode to give to open()
    :return: the parsed file or default value on error if possible
    """
    try:
        with open(file_path, open_mode) as open_file:
            return json.load(open_file)
    except PermissionError as err:
        if raise_errors:
            raise
        octobot_commons.logging.get_logger(LOGGER_NAME).error(
            f"Permission error when reading {file_path} file: {err}."
        )
    except Exception as err:
        if raise_errors:
            raise
        octobot_commons.logging.get_logger(LOGGER_NAME).exception(
            f"Unexpected error when reading {file_path} file: {err}."
        )
    if on_error_value is None:
        raise ValueError("on_error_value is unset")
    return on_error_value


def safe_dump(content: dict, save_path: str) -> None:
    """
    Safely dump content into save_path restoring the previous content if writing fails
    """
    restore_file = f"{save_path}{octobot_commons.constants.SAFE_DUMP_SUFFIX}"
    has_restore_file = False
    try:
        if os.path.exists(save_path):
            if os.path.exists(restore_file):
                os.remove(restore_file)
            # prepare a restoration file
            shutil.copy(save_path, restore_file)
            has_restore_file = True
    except Exception as err:
        # when failing to create restore file
        error_details = (
            f"Failed to create {restore_file} backup file. Is the associated "
            f"folder accessible ? : {err} ({err.__class__.__name__}) Continuing anyway."
        )
        octobot_commons.logging.get_logger(LOGGER_NAME).exception(
            err, True, error_details
        )
    try:
        # create config content as str before opening file not to clear it on json dump exception
        str_content = dump_formatted_json(content)
        with open(save_path, "w") as write_file:
            write_file.write(str_content)

    except Exception as global_exception:
        # when failing to save the new file config
        octobot_commons.logging.get_logger(LOGGER_NAME).error(
            f"File save failed : {global_exception}. "
            f"{'restoring previous content' if has_restore_file else 'no previous content to restore'}"
        )
        if has_restore_file:
            # restore file with previous content
            shutil.copy(restore_file, save_path)
        raise global_exception
    finally:
        # remove temporary restore file if any
        try:
            if os.path.exists(restore_file):
                os.remove(restore_file)
        except Exception as err:
            octobot_commons.logging.get_logger(LOGGER_NAME).exception(
                err, True, f"Failed to remove {restore_file} restore file: {err}"
            )


def dump_formatted_json(json_data) -> str:
    """
    The dumped json data
    :param json_data: the json data to be dumped
    :return: the dumped json data
    """
    return json.dumps(json_data, indent=4, sort_keys=True)
