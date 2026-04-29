#  Drakkar-Software OctoBot
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


import sys
import os
import platform
import ctypes

import octobot_commons.constants as constants
import octobot_commons.enums as enums

try:
    import psutil
except ImportError:
    if constants.USE_MINIMAL_LIBS:
        # mock psutil imports
        class PsutilImportMock:
            class virtual_memory:  # pylint: disable=invalid-name
                def __init__(self, *args):
                    raise ImportError("psutil not installed")

                def __getitem__(self, key):
                    return self[key]

            class Process:
                def __init__(self, *args):
                    raise ImportError("psutil not installed")

                def memory_full_info(self):  # pylint: disable=missing-function-docstring
                    class MemoryInfo:
                        def __init__(self, *args): # pylint: disable=unused-argument
                            self.rss = 0
                            self.vms = 0
                            self.uss = 0

                    return MemoryInfo()

            class cpu_percent:  # pylint: disable=invalid-name
                def __init__(self, *args):
                    raise ImportError("psutil not installed")

        psutil = PsutilImportMock()
    else:
        raise


def get_current_platform():
    """
    Return the current platform details
    Return examples
    For Windows :
    >>> 'Windows:10:AMD64'
    For Linux :
    >>> 'Linux:4.15.0-46-generic:x86_64'
    For Raspberry :
    >>> 'Linux:4.14.98-v7+:armv7l'
    :return: the current platform details
    """
    return (
        f"{platform.system()}{constants.PLATFORM_DATA_SEPARATOR}{platform.release()}{constants.PLATFORM_DATA_SEPARATOR}"
        f"{platform.machine()}"
    )


def get_octobot_type():
    """
    Return OctoBot running type from OctoBotTypes
    :return: the OctoBot running type
    """
    try:
        execution_arg = sys.argv[0]
        # sys.argv[0] is always the name of the python script called when using a command "python xyz.py"
        if execution_arg.endswith(".py"):
            if _is_on_docker():
                return enums.OctoBotTypes.DOCKER.value
            return enums.OctoBotTypes.PYTHON.value
        # sys.argv[0] is the name of the binary when using a binary version: ends with nothing or .exe"
        return enums.OctoBotTypes.BINARY.value
    except IndexError:
        return enums.OctoBotTypes.BINARY.value


def get_os():
    """
    Return the OS name
    :return: the OS name
    """
    return enums.PlatformsName(os.name)


def has_admin_rights() -> bool:
    """
    :return: True if the current thread has admin rights
    """
    try:
        return os.getuid() == 0
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin()


def is_machine_64bit() -> bool:
    """
    Win: AMD64
    Debian-64: x86_64
    From https://stackoverflow.com/questions/2208828/detect-64bit-os-windows-in-python
    :return: True if the machine is 64bit
    """
    return platform.machine().endswith("64")


def is_arm_machine() -> bool:
    """
    Can be armv7l or aarch64 (raspberry, Android smartphone...)
    From https://raspberrypi.stackexchange.com/questions/5100/detect-that-a-python-program-is-running-on-the-pi
    :return: True if the machine is 64bit
    """
    return platform.machine() in ["armv7l", "aarch64"]


def is_raspberry_pi_machine() -> bool:
    """
    Check if the machine is a Raspberry Pi
    Works on bare metal and in Docker containers
    :return: True if the machine is a Raspberry Pi
    """
    # Try device-tree method (works on bare metal Raspberry Pi)
    try:
        with open("/proc/device-tree/model", "r") as f:
            if "Raspberry Pi" in f.read():
                return True
    except (FileNotFoundError, IOError):
        pass

    # Fallback to cpuinfo (works in Docker containers)
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
            return "Raspberry Pi" in cpuinfo or "BCM" in cpuinfo
    except (FileNotFoundError, IOError):
        pass
    return False


def _is_on_docker():
    """
    Check if the current platform is docker
    :return: True if OctoBot is running with docker
    """
    file_to_check = "/proc/self/cgroup"
    try:
        return os.path.exists("/.dockerenv") or (
            os.path.isfile(file_to_check)
            and any("docker" in line for line in open(file_to_check))
        )
    except FileNotFoundError:
        return False


def parse_boolean_environment_var(env_key: str, default_value: str) -> bool:
    """
    Parse a boolean environment variable
    :param env_key: the environment variable key
    :param default_value: the default value
    :return: the boolean value
    """
    return constants.parse_boolean_environment_var(env_key, default_value)


def get_cpu_and_ram_usage(
    cpu_watching_seconds: float
) -> tuple[float, float, float, float, float, float]:
    """
    WARNING: blocking the current thread for the given cpu_watching_seconds seconds
    :return: the CPU usage percent, RAM usaage %, total RAM used, shared RAM used,
    virtual RAM used and unique RAM used by this process
    """
    mem_ret = psutil.virtual_memory()
    mem_info = psutil.Process(os.getpid()).memory_full_info()
    process_shared_used_ram = mem_info.rss # Resident Set Size = physical RAM used
    process_virtual_used_ram = mem_info.vms # Virtual Memory Size (ram + swap)
    process_unique_used_ram = mem_info.uss # Unique Set Size (ram without sharedmemory from other processes)
    return (
        psutil.cpu_percent(cpu_watching_seconds),
        mem_ret[2],
        mem_ret[3] / constants.BYTES_BY_GB,
        process_shared_used_ram / constants.BYTES_BY_GB,
        process_virtual_used_ram / constants.BYTES_BY_GB,
        process_unique_used_ram / constants.BYTES_BY_GB,
    )
