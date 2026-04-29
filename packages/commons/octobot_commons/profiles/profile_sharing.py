# pylint: disable=R0913,W0703
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
import os
import zipfile
import shutil
import pathlib
import uuid
import time
import requests
import octobot_commons.constants as constants
import octobot_commons.enums as enums
import octobot_commons.logging as bot_logging
import octobot_commons.errors as errors
import octobot_commons.json_util as json_util
import octobot_commons.authentication as authentication

try:
    import jsonschema
except ImportError:
    if constants.USE_MINIMAL_LIBS:
        # mock jsonschema imports
        class JsonschemaImportMock:
            class exceptions:  # pylint: disable=invalid-name
                class ValidationError(Exception):
                    def __init__(self, *args):
                        raise ImportError("jsonschema not installed")

        jsonschema = JsonschemaImportMock()
    else:
        raise
# avoid cyclic import
from octobot_commons.profiles.profile import Profile
import octobot_commons.profiles.profile_data as profile_data_import
import octobot_commons.profiles.profile_data_import as profile_data_importer


NON_OVERWRITTEN_PROFILE_FOLDERS = []
NON_OVERWRITTEN_PROFILE_FILES = [constants.PROFILE_CONFIG_FILE]
try:
    import octobot_tentacles_manager.constants as tentacles_manager_constants

    NON_OVERWRITTEN_PROFILE_FOLDERS.append(
        tentacles_manager_constants.TENTACLES_SPECIFIC_CONFIG_FOLDER
    )
except ImportError:
    pass


def export_profile(profile, export_path: str) -> str:
    """
    Exports the given profile into export_path, appends ".zip" as a file extension
    :param profile: profile to export
    :param export_path: export path ending with filename
    :return: the exported profile path including file extension
    """
    temp_path = f"{export_path}{int(time.time() * 1000)}"
    # remove any existing file to prevent any side effect
    if os.path.exists(temp_path):
        raise OSError(f"Can't export profile, the {temp_path} folder exists")
    export_path_with_ext = f"{export_path}.{constants.PROFILE_EXPORT_FORMAT}"
    if os.path.isfile(export_path_with_ext):
        os.remove(export_path_with_ext)
    # copy profile into a temp dir to edit it
    shutil.copytree(profile.path, temp_path)
    try:
        _filter_profile_export(temp_path)
        # export the edited profile
        shutil.make_archive(
            os.path.abspath(export_path), constants.PROFILE_EXPORT_FORMAT, temp_path
        )
    finally:
        shutil.rmtree(temp_path)
    return export_path_with_ext


def install_profile(
    import_path: str,
    profile_name: str,
    bot_install_path: str,
    replace_if_exists: bool,
    is_imported: bool,
    origin_url: str = None,
    quite: bool = False,
    profile_schema: str = None,
) -> Profile:
    """
    Installs the given profile export archive into the user's profile directory
    :param import_path: path to the profile zipped archive
    :param profile_name: name of the profile folder
    :param bot_install_path: path to the octobot installation
    :param replace_if_exists: when True erase the profile with the same name if it exists
    :param is_imported: when True the profile is set as imported
    :param origin_url: url the profile is coming from (if relevant)
    :param quite: when True, only log errors
    :param profile_schema: the schema to validate profile against
    :return: The created profile
    """
    logger = bot_logging.get_logger("ProfileSharing")
    target_import_path = _get_target_import_path(
        bot_install_path, profile_name, replace_if_exists
    )
    action = "Creat"
    if replace_if_exists:
        action = "Updat"
    if not quite:
        logger.info(f"{action}ing {profile_name} profile.")
    _import_profile_files(import_path, target_import_path)
    profile = Profile(target_import_path, schema_path=profile_schema).read_config()
    profile.imported = is_imported
    profile.origin_url = origin_url
    _ensure_unique_profile_id(profile)
    if is_imported:
        try:
            profile.validate()
        except jsonschema.exceptions.ValidationError as err:
            shutil.rmtree(target_import_path)
            raise errors.ProfileImportError(
                f"Invalid imported profile: {err.message} in '{'/'.join(err.absolute_path)}'"
            ) from err
    profile.save()
    if not quite:
        logger.info(f"{action}ed {profile.name} ({profile_name}) profile.")
    return profile


def import_profile(
    import_path: str,
    profile_schema: str,
    name: str = None,
    bot_install_path: str = ".",
    origin_url: str = None,
) -> Profile:
    """
    Imports the given profile export archive into the user's profile directory with the "imported_" prefix
    :param import_path: path to the profile zipped archive
    :param profile_schema: the schema to validate profile against
    :param name: name of the profile folder
    :param bot_install_path: path to the octobot installation
    :param origin_url: url the profile is coming from
    :return: The created profile
    """
    temp_profile_name = _get_profile_name(name, import_path)
    profile = install_profile(
        import_path,
        temp_profile_name,
        bot_install_path,
        False,
        True,
        origin_url=origin_url,
        profile_schema=profile_schema,
    )
    if profile.name != temp_profile_name:
        profile.rename_folder(_get_unique_profile_folder_from_name(profile), False)
    return profile


async def import_profile_data_as_profile(
    profile_data: profile_data_import.ProfileData,
    profile_schema: str,
    aiohttp_session,
    name: str = None,
    description: str = None,
    risk: enums.ProfileRisk = enums.ProfileRisk.MODERATE,
    bot_install_path: str = ".",
    origin_url: str = None,
    logo_url: str = None,
    auto_update: bool = False,
    force_simulator: bool = False,
) -> Profile:
    """
    Imports the given ProfileData into the user's profile directory with the "imported_" prefix
    :param profile_data: path to the profile zipped archive
    :param aiohttp_session: aiohttp session to use to download the profile logo
    :param profile_schema: the schema to validate profile against
    :param name: name of the profile folder
    :param description: description of the profile
    :param risk: risk of the profile
    :param bot_install_path: path to the octobot installation
    :param origin_url: url the profile is coming from
    :param logo_url: url the profile avatar
    :param auto_update: True if the profile should automatically be kept up-to-date
    :param force_simulator: True if trader simulator should be forced in config
    :return: The created profile
    """
    logger = bot_logging.get_logger("ProfileSharing")
    import_path = f"{name}-{uuid.uuid4().hex}"
    try:
        slug = profile_data.profile_details.name
        profile_data.profile_details.name = name
        profile_data_importer.init_profile_directory(import_path)
        await profile_data_importer.convert_profile_data_to_profile_directory(
            profile_data,
            import_path,
            description=description,
            risk=risk,
            auto_update=auto_update,
            slug=slug,
            avatar_url=logo_url,
            force_simulator=force_simulator,
            aiohttp_session=aiohttp_session,
        )
        return import_profile(
            import_path=import_path,
            profile_schema=profile_schema,
            name=name,
            bot_install_path=bot_install_path,
            origin_url=origin_url,
        )
    finally:
        try:
            if os.path.isdir(import_path):
                shutil.rmtree(import_path)
        except Exception as err:
            logger.exception(err, True, f"Error when removing profile temp dir: {err}")


async def update_profile(
    profile: Profile,
) -> bool:
    """
    :param profile: profile to update
    """
    authenticator = authentication.Authenticator.instance()
    profile_data = await authenticator.get_strategy_profile_data(
        None, product_slug=profile.slug
    )
    changed = profile_data_importer.get_updated_profile(profile, profile_data)
    if await profile_data_importer.convert_profile_data_to_profile_directory(
        profile_data, profile.path, profile_to_update=profile, changed=changed
    ):
        changed = True
    return changed


def download_profile(url, target_file, timeout=60):
    """
    Downloads a profile from the given url
    :param url: profile url
    :param target_file: path to save the file
    :param timeout: time given to the request before timeout
    :return: saved file path
    """
    # unauthenticated download
    with requests.get(url, stream=True, timeout=timeout) as req:
        req.raise_for_status()
        with open(target_file, "wb") as write_file:
            for chunk in req.iter_content(chunk_size=8192):
                write_file.write(chunk)
    return target_file


def download_and_install_profile(download_url, profile_schema):
    """
    :param download_url: profile url
    :param profile_schema: the schema to validate profile against
    :return: the installed profile, None if an error occurred
    """
    logger = bot_logging.get_logger("ProfileSharing")
    name = download_url.split("/")[-1]
    file_path = None
    try:
        file_path = download_profile(download_url, name)
        profile = import_profile(
            file_path, profile_schema, name=name, origin_url=download_url
        )
        logger.info(
            f"Downloaded and installed {profile.name} from {profile.origin_url}"
        )
        return profile
    except errors.UnsupportedError as err:
        logger.error(f"Error when installing profile: {err}")
        return None
    except Exception as err:
        logger.exception(err, True, f"Error when installing profile: {err}")
        return None
    finally:
        if file_path is not None and os.path.isfile(file_path):
            os.remove(file_path)


def _get_profile_name(name, import_path):
    profile_name = name or (
        f"{constants.IMPORTED_PROFILE_PREFIX}_{os.path.split(import_path)[-1]}"
    )
    return profile_name.split(f".{constants.PROFILE_EXPORT_FORMAT}")[0]


def _filter_profile_export(profile_path: str):
    profile_file = os.path.join(profile_path, constants.PROFILE_CONFIG_FILE)
    if os.path.isfile(profile_file):
        parsed_profile = json_util.read_file(profile_file)
        _filter_disabled(parsed_profile, constants.CONFIG_EXCHANGES)
        with open(profile_file, "w") as open_file:
            json.dump(parsed_profile, open_file, indent=4, sort_keys=True)


def _filter_disabled(profile_config: dict, element):
    filtered_exchanges = {
        exchange: details
        for exchange, details in profile_config[constants.PROFILE_CONFIG][
            element
        ].items()
        if details.get(constants.CONFIG_ENABLED_OPTION, True)
    }
    profile_config[constants.PROFILE_CONFIG][element] = filtered_exchanges


def _get_target_import_path(
    bot_install_path: str, profile_name: str, replace_if_exists: bool
) -> str:
    """
    Get the target profile folder path
    :param bot_install_path: path to the octobot installation
    :param profile_name: name of the profile folder
    :param replace_if_exists: when True erase the profile with the same name if it exists
    :return: (the final target import path, True if the profile is replaced)
    """
    target_import_path = os.path.join(
        bot_install_path, constants.USER_PROFILES_FOLDER, profile_name
    )
    if replace_if_exists:
        return target_import_path
    return _get_unique_profile_folder(target_import_path)


def _import_profile_files(profile_path: str, target_profile_path: str) -> None:
    """
    Copy or extract profile files to destination. Does not override local tentacles configuration
    :param profile_path: the current profile path
    :param target_profile_path: the target profile path
    :return: None
    """
    if zipfile.is_zipfile(profile_path):
        with zipfile.ZipFile(profile_path) as zipped_profile:
            for archive_member in zipped_profile.namelist():
                if _should_profile_file_be_imported(
                    target_profile_path, archive_member
                ):
                    zipped_profile.extract(archive_member, target_profile_path)
    else:
        if not os.path.isdir(profile_path):
            raise errors.UnsupportedError(
                f"Profile format not supported ({profile_path})"
            )

        def _get_ignored_elements(current_dir, sub_elements):
            return [
                element
                for element in sub_elements
                if not _should_profile_file_be_imported(
                    target_profile_path,
                    os.path.join(current_dir, element).replace(
                        f"{profile_path}{os.path.sep}", ""
                    ),  # force local path
                )
            ]

        shutil.copytree(
            profile_path,
            target_profile_path,
            ignore=_get_ignored_elements,
            dirs_exist_ok=True,
        )


def _should_profile_file_be_imported(
    target_profile_path: str, profile_file_path: str
) -> bool:
    for non_overwritten_element in NON_OVERWRITTEN_PROFILE_FOLDERS:
        # ignore files in NON_OVERWRITTEN_PROFILE_FOLDERS that already exist
        element_path = pathlib.Path(profile_file_path)
        if (
            element_path.name in NON_OVERWRITTEN_PROFILE_FILES
            or non_overwritten_element in element_path.parts[:-1]
        ) and os.path.isfile(os.path.join(target_profile_path, profile_file_path)):
            return False
    return True


def _get_unique_profile_folder_from_name(profile) -> str:
    folder = _get_unique_profile_folder(
        os.path.join(os.path.split(profile.path)[0], profile.name)
    )
    return os.path.split(folder)[1]


def _get_unique_profile_folder(target_import_path: str) -> str:
    """
    Creates an unique profile folder name
    :param target_import_path: the expected target profile folder name
    :return: the unique profile folder name
    """
    iteration = 1
    candidate = target_import_path
    while os.path.exists(candidate) and iteration < 100:
        iteration += 1
        candidate = f"{target_import_path}_{iteration}"
    return candidate


def _ensure_unique_profile_id(profile) -> None:
    """
    Ensure that no other installed profile has the same id
    :param profile: the installed profile
    :return: None
    """
    ids = Profile.get_all_profiles_ids(
        pathlib.Path(profile.path).parent, ignore=profile.path
    )
    iteration = 1
    while profile.profile_id in ids and iteration < 100:
        profile.profile_id = str(uuid.uuid4())
        iteration += 1
