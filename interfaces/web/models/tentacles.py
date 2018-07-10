from config.cst import CONFIG_TENTACLES_KEY, TENTACLE_PACKAGE_DESCRIPTION
from interfaces import get_bot
from tools.tentacle_manager.tentacle_package_manager import TentaclePackageManager
from tools.tentacle_manager.tentacle_package_util import get_is_url, get_package_name, \
    get_octobot_tentacle_public_repo, get_package_description_with_adaptation
from tools.tentacle_manager.tentacle_manager import TentacleManager


def get_tentacles_packages():
    default_tentacles_repo_desc_file = get_octobot_tentacle_public_repo()
    default_tentacles_repo = get_octobot_tentacle_public_repo(False)
    packages = {
        default_tentacles_repo: get_package_name(default_tentacles_repo_desc_file,
                                                 get_is_url(default_tentacles_repo_desc_file))
    }
    for tentacle_package in get_bot().get_config()[CONFIG_TENTACLES_KEY]:
        packages[tentacle_package] = get_package_name(tentacle_package, get_is_url(tentacle_package))
    return packages


def get_tentacles_package_description(path_or_url):
    try:
        return get_package_description_with_adaptation(path_or_url)[TENTACLE_PACKAGE_DESCRIPTION]
    except Exception:
        return None


def register_and_install(path_or_url):
    config = get_bot().get_config()
    config[CONFIG_TENTACLES_KEY].append(path_or_url)
    # TODO update config.json

    tentacles_manager = TentacleManager(config)
    tentacles_manager.install_tentacle_package(path_or_url, True)
    return True


def get_tentacles():
    return TentaclePackageManager.get_installed_modules()