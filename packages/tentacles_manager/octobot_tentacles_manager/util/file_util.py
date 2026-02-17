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
import aiofiles
import os
import os.path as path
import hashlib
import datetime
import shutil

import octobot_commons.logging as commons_logging
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.tentacle_filter as tentacle_filter


def get_file_creation_time(file_path) -> str:
    try:
        return datetime.datetime.fromtimestamp(os.path.getctime(file_path)).replace(
            tzinfo=datetime.timezone.utc
        ).isoformat()
    except Exception as err:
        commons_logging.get_logger("tentacles_fetching").exception(
            err, True, f"Error when computing {file_path} creation date: {err}"
        )
    return ""


async def log_tentacles_file_details(tentacles_file, last_modified):
    try:
        if path.isfile(tentacles_file):
            async with aiofiles.open(tentacles_file, "rb") as file:
                file_hash = hashlib.sha256(await file.read()).hexdigest()
            commons_logging.get_logger("tentacles_fetching").info(
                f"Tentacles package {tentacles_file if isinstance(tentacles_file, str) else tentacles_file.name}: "
                f"last_modified: {last_modified}, file_hash: {file_hash}"
            )
        elif path.isdir(tentacles_file):
            for entry in os.scandir(tentacles_file):
                await log_tentacles_file_details(entry, last_modified)
    except Exception as err:
        commons_logging.get_logger("tentacles_fetching").exception(
            err, True, f"Error when computing {tentacles_file} file details: {err}"
        )

async def find_or_create(path_to_create, is_directory=True, file_content=""):
    if not path.exists(path_to_create):
        if is_directory:
            if not path.isdir(path_to_create):
                os.makedirs(path_to_create)
        else:
            if not path.isfile(path_to_create):
                # should be used for python init.py files only
                async with aiofiles.open(path_to_create, "w+") as file:
                    await file.write(file_content)
        return True
    return False


async def find_or_create_with_empty_init_file(path_to_create, is_directory=True, file_content=""):
    created = await find_or_create(path_to_create, is_directory=is_directory, file_content=file_content)
    if os.path.exists(path_to_create) and os.path.isdir(path_to_create):
        init_file = path.join(path_to_create, constants.PYTHON_INIT_FILE)
        if not path.exists(init_file):
            # create empty init file
            open(init_file, 'w').close()
            created = True
    return created


async def replace_with_remove_or_rename(new_file_or_dir_entry, dest_file_or_dir):
    try:
        if path.isfile(dest_file_or_dir):
            os.remove(dest_file_or_dir)
        else:
            if path.exists(dest_file_or_dir):
                shutil.rmtree(dest_file_or_dir)
    except PermissionError:
        # can't remove file / folder: might be locked (ex: .pyd files)
        # move it into TO_REMOVE_FOLDER for it to be deleted afterwards
        dest_path, dest_file = path.split(dest_file_or_dir)
        to_rm_folder = path.join(dest_path, constants.TO_REMOVE_FOLDER)
        await find_or_create(to_rm_folder, is_directory=True)
        shutil.move(dest_file_or_dir, path.join(to_rm_folder, dest_file))
    if path.isfile(new_file_or_dir_entry):
        shutil.copyfile(new_file_or_dir_entry, dest_file_or_dir)
    else:
        shutil.copytree(new_file_or_dir_entry, dest_file_or_dir)


async def copy_with_include_filter(source_path, dest_path, include_patterns):    
    ignore_func = tentacle_filter.should_include_ignore_function(source_path, include_patterns)
    for entry in os.scandir(source_path):
        if entry.name in ignore_func(source_path, [entry.name]):
            continue
        
        dest = path.join(dest_path, entry.name)
        
        if entry.is_file():
            await replace_with_remove_or_rename(entry, dest)
        else:
            if path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(entry, dest, ignore=ignore_func)


def merge_folders(to_merge_folder, dest_folder, ignore_func=None):
    dest_folder_elements = {
        element.name: element for element in os.scandir(dest_folder)
    }
    elements = list(os.scandir(to_merge_folder))
    ignored_elements = ignore_func(to_merge_folder, (e.name for e in elements)) if ignore_func is not None else []
    filtered_elements = [element
                         for element in elements
                         if element.name not in ignored_elements]
    for element in filtered_elements:
        dest = path.join(dest_folder, element.name)
        if element.is_file():
            shutil.copy(element.path, dest)
        else:
            if element.name not in dest_folder_elements:
                shutil.copytree(element.path, dest, ignore=ignore_func if ignore_func is not None else None)
            else:
                merge_folders(element.path, dest_folder_elements[element.name].path, ignore_func=ignore_func)
