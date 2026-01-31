#  Drakkar-Software OctoBot-Interfaces
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
import flask

import octobot_commons.logging as logging


_WEBHOOKS_CALLBACKS = []


def register_webhook(callback):
    _WEBHOOKS_CALLBACKS.append(callback)


def has_webhook(callback):
    return callback in _WEBHOOKS_CALLBACKS


def register(blueprint):
    @blueprint.route("/webhook/<identifier>", methods=['POST'])
    def webhook(identifier):
        try:
            for callback in _WEBHOOKS_CALLBACKS:
                try:
                    callback(identifier)
                except Exception as err:
                    logging.get_logger(__name__).exception(err, True, f"Error when calling webhook: {err}")
            return '', 200
        except KeyError:
            flask.abort(500)
