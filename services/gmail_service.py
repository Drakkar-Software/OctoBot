import smtplib
import email.message

from config.cst import *
from services import AbstractService


class GmailService(AbstractService):
    def __init__(self):
        super().__init__()
        self.gmail_api = None

    @staticmethod
    def is_setup_correctly(config):
        if CONFIG_GMAIL in config[CONFIG_CATEGORY_SERVICES] \
                and CONFIG_SERVICE_INSTANCE in config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]:
            return True
        else:
            return False

    def has_required_configuration(self):
        return CONFIG_CATEGORY_SERVICES in self.config \
               and CONFIG_GMAIL in self.config[CONFIG_CATEGORY_SERVICES] \
               and "gmail_user" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL] \
               and "gmail_password" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL] \
               and "mail_dest" in self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]

    def get_endpoint(self):
        return self.gmail_api

    def get_type(self):
        return CONFIG_GMAIL

    def prepare(self):
        if not self.gmail_api:
            try:
                self.gmail_api = smtplib.SMTP("smtp.gmail.com", 587)
                self.gmail_api.starttls()
                self.gmail_api.login(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_user"],
                                     self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_password"])
            except Exception as e:
                self.logger.error("Failed to prepare mail service : {0}".format(e))

    def send_mail(self, subject, content):
        try:
            msg = email.message.Message()
            msg.add_header('Content-Type', 'text/plain')
            msg['From'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_user"] + "@gmail.com"
            msg.set_payload(content)
            msg['Subject'] = subject
            msg['To'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["mail_dest"]
            self.gmail_api.sendmail(msg['From'], msg['To'], msg.as_string())
            return True
        except Exception as e:
            self.logger.error("Failed to send mail : {0}".format(e))
            self.stop()
            self.prepare()
            return False

    def stop(self):
        self.gmail_api = None
