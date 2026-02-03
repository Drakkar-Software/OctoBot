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
import flask_login
import flask_wtf
import wtforms

import octobot_commons.logging as bot_logging
import octobot_commons.authentication as authentication
import tentacles.Services.Interfaces.web_interface.login as web_login
import tentacles.Services.Interfaces.web_interface.security as security

logger = bot_logging.get_logger("ServerInstance Controller")


def register(blueprint):
    @blueprint.route('/login', methods=['GET', 'POST'])
    def login():
        # use default constructor to apply default values when no form in request
        form = LoginForm(flask.request.form) if flask.request.form else LoginForm()
        if form.validate_on_submit():
            if blueprint.login_manager.is_valid_password(
                    flask.request.remote_addr,
                    form.password.data,
                    form
            ):
                blueprint.login_manager.login_user(form.remember_me.data)
                web_login.reset_attempts(flask.request.remote_addr)

                return _get_next_url_or_home_redirect()
            if web_login.register_attempt(flask.request.remote_addr):
                if not form.password.errors:
                    form.password.errors.append('Invalid password')
                logger.warning(f"Invalid login attempt from : {flask.request.remote_addr}")
            else:
                form.password.errors.append('Too many attempts. Please restart your OctoBot to be able to login.')
        return flask.render_template(
            'login.html',
            form=form,
            is_remote_login=authentication.Authenticator.instance().must_be_authenticated_through_authenticator()
        )


    @blueprint.route("/logout")
    @flask_login.login_required
    def logout():
        flask_login.logout_user()
        return _get_next_url_or_home_redirect()


    def _get_next_url_or_home_redirect():
        next_url = flask.request.args.get('next')
        if not security.is_safe_url(next_url):
            return flask.abort(400)
        return flask.redirect(next_url or flask.url_for('home'))


class LoginForm(flask_wtf.FlaskForm):
    password = wtforms.PasswordField('Password')
    remember_me = wtforms.BooleanField('Remember me', default=True)
