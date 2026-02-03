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


class User:
    """
    Docs from https://flask-login.readthedocs.io/en/latest/#your-user-class
    """
    GENERIC_USER_ID = "user"

    def __init__(self):
        # This property should return True if the user is authenticated, i.e. they have provided valid credentials.
        # (Only authenticated users will fulfill the criteria of login_required.)
        self.is_authenticated = False
        # This property should return True if this is an active user - in addition to being authenticated, they also
        # have activated their account, not been suspended, or any condition your application has for rejecting
        # an account. Inactive accounts may not log in (without being forced of course).
        self.is_active = True
        # This property should return True if this is an anonymous user. (Actual users should return False instead.)
        self.is_anonymous = False

    def get_id(self):
        """
        This method must return a unicode that uniquely identifies this user, and can be used to load the user
        from the user_loader callback. Note that this must be a unicode - if the ID is natively an int or some other
        type, you will need to convert it to unicode.
        :return: The only octoBot user id
        """
        return self.GENERIC_USER_ID
