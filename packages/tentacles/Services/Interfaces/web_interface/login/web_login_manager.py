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
import functools
import flask_login
import flask

import octobot_commons.configuration as configuration
import octobot_commons.authentication as authentication
import octobot_commons.logging as logging
import octobot_services.interfaces.util as interfaces_util
import octobot.constants as constants
import tentacles.Services.Interfaces.web_interface.login as login

GENERIC_USER = login.User()
_IS_LOGIN_REQUIRED = True
IP_TO_CONNECTION_ATTEMPTS = {}
MAX_CONNECTION_ATTEMPTS = 50


class WebLoginManager(flask_login.LoginManager):
    def __init__(self, flask_app, password_hash):
        # force is_authenticated to save login state throughout server restart
        GENERIC_USER.is_authenticated = True
        flask_login.LoginManager.__init__(self)
        self.init_app(flask_app)
        self.password_hash = password_hash
        # register login view to redirect to when login is required
        self.login_view = "/login"
        self._register_callbacks()

    def login_user(self, remember=False, duration=None, **kwargs):
        # still set is_authenticated to be sure it's True on login
        GENERIC_USER.is_authenticated = True
        flask_login.login_user(GENERIC_USER, remember=remember, duration=duration, **kwargs)

    def is_valid_password(self, ip, password, form):
        authenticator = authentication.Authenticator.instance()
        if authenticator.must_be_authenticated_through_authenticator():
            try:
                if constants.USER_ACCOUNT_EMAIL is None:
                    raise authentication.AuthenticationError("Login impossible. "
                                                             "USER_ACCOUNT_EMAIL constant must to be set")
                interfaces_util.run_in_bot_main_loop(
                    authenticator.login(constants.USER_ACCOUNT_EMAIL, password),
                    log_exceptions=False
                )
                return not is_banned(ip)
            except authentication.FailedAuthentication:
                return False
            except Exception as e:
                logging.get_logger("WebLoginManager").exception(e, False)
                form.password.errors.append(f"Error during authentication: {e}")
                return False
        return not is_banned(ip) and configuration.get_password_hash(password) == self.password_hash

    def _register_callbacks(self):
        @self.user_loader
        def load_user(_):
            # return None if user is invalid
            return GENERIC_USER


def is_authenticated():
    return flask_login.current_user.is_authenticated


def set_is_login_required(login_required):
    global _IS_LOGIN_REQUIRED
    _IS_LOGIN_REQUIRED = login_required


def is_login_required():
    return _IS_LOGIN_REQUIRED or authentication.Authenticator.instance().must_be_authenticated_through_authenticator()


@flask_login.login_required
def _login_required_func(func, *args, **kwargs):
    return func(*args, **kwargs)


def login_required_when_activated(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if is_login_required():
            return _login_required_func(func, *args, **kwargs)
        return func(*args, **kwargs)
    return decorated_view


def active_login_required(func):
    @functools.wraps(func)
    def decorated_view(*args, **kwargs):
        if is_login_required():
            return _login_required_func(func, *args, **kwargs)
        flask.flash(f"For security reasons, please enable password authentication in "
                    f"accounts configuration to use the {flask.request.path} page.",
                    category=flask_login.LOGIN_MESSAGE_CATEGORY)
        return flask.redirect('home')
    return decorated_view


def register_attempt(ip):
    if ip in IP_TO_CONNECTION_ATTEMPTS:
        IP_TO_CONNECTION_ATTEMPTS[ip] += 1
    else:
        IP_TO_CONNECTION_ATTEMPTS[ip] = 1
    return not is_banned(ip)


def is_banned(ip):
    if ip in set(IP_TO_CONNECTION_ATTEMPTS.keys()):
        return IP_TO_CONNECTION_ATTEMPTS[ip] >= MAX_CONNECTION_ATTEMPTS
    return False


def reset_attempts(ip):
    IP_TO_CONNECTION_ATTEMPTS[ip] = 0
