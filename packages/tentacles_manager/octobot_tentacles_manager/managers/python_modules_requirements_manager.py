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
import asyncio
import os.path as path
import sys

import octobot_commons.enums as enums
import octobot_commons.logging as logging
import octobot_commons.os_util as os_util


# TODO: adapt this wrapper to handle python modules requirements
# Warning: Impossible to dynamically load python modules with unmet dependencies in frozen python environment
# (ex: compiled binary). However these dynamic imports work with Python / Docker environment.
# code from pip POC (https://github.com/Drakkar-Software/OctoBot-Tentacles-Manager/tree/pip-usage-poc)

# TODO: remove from to .coveragerc when adapted

"""
Tentacles management
"""


async def install_tentacle(tentacle_path: str, tentacle_name: str) -> (str, str):
    return await _run_pip_install(path.join(tentacle_path, "Trading"), tentacle_name)


async def update_tentacle(tentacle_path: str, tentacle_name: str) -> (str, str):
    return await _run_pip_update(path.join(tentacle_path, "Trading"), tentacle_name)


async def list_installed_tentacles(tentacle_path: str) -> list:
    return [await _run_pip_freeze(path.join(tentacle_path, tentacle_type_path))
            for tentacle_type_path in ["Trading"]]

"""
Pip wrapper
"""


async def _run_pip_command(args) -> (str, str):
    if os_util.get_octobot_type() == enums.OctoBotTypes.BINARY.value:
        raise RuntimeError("Can't use PIP in a frozen binary environment")
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "pip", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Status
    logging.get_logger().info(f"Started: {args}, pid={process.pid}")

    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()

    # Progress
    if process.returncode == 0:
        logging.get_logger().info(f"Done: {args}, pid={process.pid}")
    else:
        logging.get_logger().error(f"Failed: {args}, pid={process.pid}, result: {_parse_pip_command_result(stderr)}")

    return stdout, stderr


"""
Pip freeze wrapper
"""


def _get_pip_freeze_args(path: str = None) -> list:
    args = ["freeze"]
    if path is not None:
        args.append("--path")
        args.append(path)
    return args


async def _run_pip_freeze(path: str = None) -> (str, str):
    return await _run_pip_command(_get_pip_freeze_args(path=path))


"""
Pip install wrapper
"""


def _get_pip_install_args(path: str = None, package_name: str = None) -> list:
    args = ["install"]
    if path is not None:
        args.append("-t")
        args.append(path)
    if package_name is not None:
        args.append(package_name)
    return args


async def _run_pip_install(path: str = None, package_name: str = None) -> (str, str):
    return await _run_pip_command(_get_pip_install_args(path=path, package_name=package_name))


"""
Pip update wrapper
"""


def _get_pip_update_args(path: str = None, package_name: str = None) -> list:
    args = _get_pip_install_args(path=path, package_name=package_name)
    args.append("-U")
    return args


async def _run_pip_update(path: str = None, package_name: str = None) -> (str, str):
    return await _run_pip_command(_get_pip_update_args(path=path, package_name=package_name))


"""
Pip utils
"""


def _parse_pip_command_result(stdout) -> str:
    return stdout.decode().strip()
