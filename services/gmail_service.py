import smtplib
import email.message

from config.cst import *
from services import AbstractService


class GmailService(AbstractService):
    REQUIRED_CONFIG = ["gmail_user", "gmail_password", "mail_dest"]

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
            self.gmail_con.login(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_user"],
                                 self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_password"])
        except Exception as e:
            self.logger.error("Failed to connect to gmail service : {0}".format(e))

    def send_mail(self, subject, content):
        try:
            self.prepare()
            msg = email.message.Message()
            msg.add_header('Content-Type', 'text/plain')
            msg['From'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["gmail_user"] + "@gmail.com"
            msg.set_payload(content)
            msg['Subject'] = subject
            msg['To'] = self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["mail_dest"]
            self.gmail_con.sendmail(msg['From'], msg['To'], msg.as_string())
            self.gmail_con.close()
            return True
        except Exception as e:
            self.logger.error("Failed to send mail : {0}".format(e))
            return False

    def get_successful_startup_message(self):
        return "Successfully initialized to notify {0}." \
            .format(self.config[CONFIG_CATEGORY_SERVICES][CONFIG_GMAIL]["mail_dest"])
