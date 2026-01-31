# pylint: disable=C0116
#  Drakkar-Software OctoBot-Trading
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
import octobot_commons.signals.signal as signal
import octobot_commons.signals.signal_bundle as signal_bundle
import octobot_commons.signals.signal_dependencies as signal_dependencies
import octobot_commons.enums as commons_enums


def create_signal_bundle(signal_bundle_dict: dict) -> signal_bundle.SignalBundle:
    signal_bundle_value = signal_bundle_dict[
        commons_enums.CommunityFeedAttrs.VALUE.value
    ]
    return signal_bundle.SignalBundle(
        signal_bundle_value.get(commons_enums.SignalBundlesAttrs.IDENTIFIER.value),
        signals=[
            create_signal(s)
            for s in signal_bundle_value.get(
                commons_enums.SignalBundlesAttrs.SIGNALS.value, []
            )
        ],
        version=signal_bundle_value.get(commons_enums.SignalBundlesAttrs.VERSION.value),
    )


def create_signal(signal_dict: dict) -> signal.Signal:
    return signal.Signal(
        signal_dict.get(commons_enums.SignalsAttrs.TOPIC.value),
        signal_dict.get(commons_enums.SignalsAttrs.CONTENT.value),
        (
            signal_dependencies.SignalDependencies(
                signal_dict.get(commons_enums.SignalsAttrs.DEPENDENCIES.value).get(
                    commons_enums.SignalDependenciesAttrs.DEPENDENCY.value
                )
            )
            if signal_dict.get(commons_enums.SignalsAttrs.DEPENDENCIES.value)
            else None
        ),
    )
