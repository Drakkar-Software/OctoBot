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

import smtplib
import email.message

from config import *
from services import AbstractService


class GmailService(AbstractService):
    GMAIL_USER = "gmail-user"
    GMAIL_PASSWORD = "gmail-password"
    MAIL_DEST = "mail-dest"

    REQUIRED_CONFIG = [GMAIL_USER, GMAIL_PASSWORD, MAIL_DEST]

    # Used in configuration interfaces
    CONFIG_FIELDS_DESCRIPTION = {
        GMAIL_USER: "Your gmail username (to send emails from this account).",
        GMAIL_PASSWORD: "Your gmail password (to send emails from this account).",
        MAIL_DEST: "The destination email address (to send emails to this account)."
    }
    CONFIG_DEFAULT_VALUE = {
        GMAIL_USER: "",
        GMAIL_PASSWORD: "",
        MAIL_DEST: ""
    }
    HELP_PAGE = "https://github.com/Drakkar-Software/OctoBot/wiki/Gmail-interface#gmail-interface"

    def __init__(self):
        super().__init__()
        self.gmail_con = None

    @staticmethod
    def is_setup_correctly(config):
        return CONFIG_GMAIL in config[CONFIG_CATEGORY_SERVICES] \
               and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_GMAIL in self.config[CONFIG_CATEGORY_SERVICES] \
               and self.check_required_config(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL])

    def get_endpoint(self):
        return self.gmail_con

    def get_type(self):
        return CONFIG_GMAIL

    def prepare(self):
        try:
            self.gmail_con = smtplib.SMTP()
            self.gmail_con.connect("smtp.gmail.com", 587)
            self.gmail_con.ehlo()
            self.gmail_con.starttls()
            self.gmail_con.ehlo()
            self.gmail_con.login(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][self.GMAIL_USER],
                                 self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][self.GMAIL_PASSWORD])
        except Exception as e:
            self.logger.error("Failed to connect to gmail service : {0}".format(e))

    def send_mail(self, subject, content):
        try:
            self.prepare()
            msg = email.message.Message()
            msg.add_header('Content-Type', 'text/plain')
            msg['From'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][self.GMAIL_USER] + "@gmail.com"
            msg.set_payload(content)
            msg['Subject'] = subject
            msg['To'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][self.MAIL_DEST]
            self.gmail_con.sendmail(msg['From'], msg['To'], msg.as_string())
            self.gmail_con.close()
            return True
        except Exception as e:
            self.logger.error("Failed to send mail : {0}".format(e))
            return False

    def get_successful_startup_message(self):
        return f"Successfully initialized to notify " \
                   f"{self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL][self.MAIL_DEST]}.", True
