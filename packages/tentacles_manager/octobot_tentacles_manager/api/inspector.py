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
import packaging.version as packaging_version

import octobot_commons.logging as logging
import octobot_commons.tentacles_management as tentacles_management

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.loaders as loaders
import octobot_tentacles_manager.util as util


def get_installed_tentacles_modules() -> set:
    return set(tentacle for tentacle in loaders.get_tentacle_classes().values())


def get_tentacle_group(klass) -> str:
    return loaders.get_tentacle(klass).tentacle_group


def get_tentacle_version(klass) -> str:
    return loaders.get_tentacle(klass).version


def get_tentacle_origin_package(klass) -> str:
    return loaders.get_tentacle(klass).origin_package


def get_tentacle_module_name(klass) -> str:
    return loaders.get_tentacle(klass).name


def get_tentacle_classes_requirements(klass) -> list:
    requirements = loaders.get_tentacle(klass).extract_tentacle_requirements()
    classes = []
    for requirement in requirements:
        for tentacle_name in loaders.get_tentacles_classes_names_from_tentacle_module(requirement[0]):
            try:
                classes += [get_tentacle_class_from_string(tentacle_name)]
            except RuntimeError:
                # some tentacles can't be found this way (ex: util tentacles), ignore them
                pass
    return classes


def get_tentacle_resources_path(klass) -> str:
    return loaders.get_resources_path(klass)


def get_tentacle_documentation_path(klass) -> str:
    return loaders.get_documentation_file_path(klass)


def get_tentacle_documentation(klass) -> str:
    return loaders.get_documentation(klass)


def check_tentacle_version(version, name, origin_package, verbose=True) -> bool:
    logger = logging.get_logger("TentacleChecker")
    try:
        if origin_package == constants.DEFAULT_TENTACLES_PACKAGE:
            if packaging_version.Version(version) < packaging_version.Version(
                    constants.TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION) and verbose:
                logger.error(f"Incompatible tentacle {name}: version {version}, "
                             f"minimum expected: {constants.TENTACLE_CURRENT_MINIMUM_DEFAULT_TENTACLES_VERSION} "
                             f"this tentacle may not work properly. "
                             f"Please update your tentacles ('start.py -p update {name}' "
                             f"or 'start.py -p update all')")
                return False
    except Exception as e:
        if verbose:
            logger.error(f"Error when reading tentacle metadata: {e}")
    return True


def _load_tentacle_class(tentacle_name):
    # Lazy import of tentacles to let tentacles manager handle imports
    try:
        import octobot_evaluators.evaluators as evaluators
        import tentacles.Evaluator as tentacles_Evaluator
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, evaluators.StrategyEvaluator,
            tentacles_Evaluator.Strategies, tentacles_management.evaluator_parent_inspection):
            return tentacle_class
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, evaluators.TAEvaluator,
            tentacles_Evaluator.TA, tentacles_management.evaluator_parent_inspection):
            return tentacle_class
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, evaluators.SocialEvaluator,
            tentacles_Evaluator.Social, tentacles_management.evaluator_parent_inspection):
            return tentacle_class
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, evaluators.RealTimeEvaluator,
            tentacles_Evaluator.RealTime, tentacles_management.evaluator_parent_inspection):
            return tentacle_class
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, evaluators.ScriptedEvaluator,
            tentacles_Evaluator.Scripted, tentacles_management.evaluator_parent_inspection):
            return tentacle_class
        import octobot_trading.modes as trading_modes
        import tentacles.Trading as tentacles_trading
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, trading_modes.AbstractTradingMode,
            tentacles_trading.Mode, tentacles_management.trading_mode_parent_inspection):
            return tentacle_class
        import octobot_trading.exchanges as trading_exchanges
        if tentacle_class := tentacles_management.get_class_from_string(
            tentacle_name, trading_exchanges.AbstractExchange,
            tentacles_trading.Exchange, tentacles_management.default_parents_inspection):
            return tentacle_class
        try:
            import tentacles.Services.Interfaces.web_interface.plugins as web_plugins
            import tentacles.Services as tentacles_services
            if tentacle_class := tentacles_management.get_class_from_string(
                tentacle_name, web_plugins.AbstractWebInterfacePlugin,
                tentacles_services.Interfaces, tentacles_management.default_parents_inspection):
                return tentacle_class
        except ImportError:
            pass
        try:
            return util.get_tentacle_class_from_extra_tentacles(tentacle_name)
        except KeyError:
            pass
        raise RuntimeError(f"Can't find tentacle: {tentacle_name}")
    except ImportError as e:
        raise ImportError(f"Can't import {e} module which is required to get associated "
                          f"tentacles classes") from e


def get_tentacle_class_from_string(tentacle_name, allow_cache=True):
    if allow_cache:
        try:
            return loaders.get_tentacle_class_from_name(tentacle_name)
        except KeyError:
            tentacle_class = _load_tentacle_class(tentacle_name)
            loaders.set_tentacle_class_by_name(tentacle_name, tentacle_class)
            return tentacle_class
    return _load_tentacle_class(tentacle_name)


def get_tentacles_classes_names_for_type(tentacle_type) -> list:
    return loaders.get_tentacles_classes_names_for_type(tentacle_type)


def get_installed_packages_from_url(tentacles_package_manager, url: str) -> list[str]:
    return tentacles_package_manager.get_installed_packages_from_url(url)


def get_all_installed_package_urls(tentacles_package_manager) -> list[str]:
    return tentacles_package_manager.get_all_installed_package_urls()


def get_tentacles_from_package_name(package_name: str) -> list[str]:
    return [
        tentacle.name
        for tentacle in get_installed_tentacles_modules()
        if tentacle.origin_package == package_name
    ]
