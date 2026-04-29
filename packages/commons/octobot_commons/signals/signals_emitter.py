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
import octobot_commons.enums as commons_enums
import octobot_commons.authentication as authentication
import octobot_commons.signals.signal_bundle as signal_bundle


async def emit_signal_bundle(to_send_signal_bundle: signal_bundle.SignalBundle):
    """
    Emits a signal bundle
    """
    await authentication.Authenticator.instance().send(
        to_send_signal_bundle.to_dict(),
        commons_enums.CommunityChannelTypes.SIGNAL,
        identifier=to_send_signal_bundle.identifier,
    )
