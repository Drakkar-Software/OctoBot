import logging

from telegram.ext import CommandHandler, MessageHandler, Filters

from config.cst import *
from interfaces import get_reference_market
from interfaces.util import get_portfolio_current_value


class TelegramApp:
    def __init__(self, config, telegram_service, telegram_updater):
        self.config = config
        self.telegram_service = telegram_service
        self.telegram_updater = telegram_updater
        self.dispatcher = self.telegram_updater.dispatcher
        self.logger = logging.getLogger(self.__class__.__name__)

        self.add_handlers()

        # Start the Bot
        self.telegram_updater.start_polling()

    def add_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self.command_start))
        self.dispatcher.add_handler(CommandHandler("portfolio", self.command_portfolio))

        # log all errors
        self.dispatcher.add_error_handler(self.command_error)

        # TEST : unhandled messages
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.echo))

    @staticmethod
    def command_start(_, update):
        update.message.reply_text("Hello, I'm CryptoBot, type /help to know my skills.")

    @staticmethod
    def command_portfolio(_, update):
        portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
        reference_market = get_reference_market()

        update.message.reply_text("Portfolio real value : {0} {1}".format(portfolio_real_current_value,
                                  reference_market))
        update.message.reply_text("Portfolio simulated value : {0} {1}".format(portfolio_real_current_value,
                                  reference_market))

    @staticmethod
    def command_error(_, update):
        update.message.reply_text("Failed to perform this command : {0}".format(update.message.text))

    @staticmethod
    def help(_, update):
        update.message.reply_text("...")

    @staticmethod
    def echo(_, update):
        update.message.reply_text(update.message.text)

    @staticmethod
    def enable(config):
        if CONFIG_INTERFACES not in config:
            config[CONFIG_INTERFACES] = {}
        if CONFIG_INTERFACES_TELEGRAM not in config[CONFIG_INTERFACES]:
            config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] = {}
        config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION] = True

    @staticmethod
    def is_enabled(config):
        return CONFIG_INTERFACES in config \
               and CONFIG_INTERFACES_TELEGRAM in config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] \
               and config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION]
