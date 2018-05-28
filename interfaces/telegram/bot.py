import datetime
import logging

from telegram.ext import CommandHandler, MessageHandler, Filters

from config.cst import *
from interfaces import get_reference_market, get_bot
from interfaces.trading_util import get_portfolio_current_value, get_open_orders, get_trades_history, \
    get_global_portfolio_currencies_amounts, set_risk, get_risk, get_global_profitability, get_currencies_with_status, \
    cancel_all_open_orders, set_enable_trading
from tools.commands import Commands
from tools.pretty_printer import PrettyPrinter


class TelegramApp:
    EOL = "\n"

    def __init__(self, config, telegram_service, telegram_updater):
        self.config = config
        self.paused = False
        self.telegram_service = telegram_service
        self.telegram_updater = telegram_updater
        self.dispatcher = self.telegram_updater.dispatcher
        self.logger = logging.getLogger(self.__class__.__name__)

        self.add_handlers()

        # Start the Bot
        self.telegram_updater.start_polling()

    def add_handlers(self):
        self.dispatcher.add_handler(CommandHandler("start", self.command_start))
        self.dispatcher.add_handler(CommandHandler("ping", self.command_ping))
        self.dispatcher.add_handler(CommandHandler(["portfolio", "pf"], self.command_portfolio))
        self.dispatcher.add_handler(CommandHandler(["open_orders", "oo"], self.command_open_orders))
        self.dispatcher.add_handler(CommandHandler(["trades_history", "th"], self.command_trades_history))
        self.dispatcher.add_handler(CommandHandler(["profitability", "pb"], self.command_profitability))
        self.dispatcher.add_handler(CommandHandler("set_risk", self.command_risk))
        self.dispatcher.add_handler(CommandHandler(["market_status", "ms"], self.command_market_status))
        self.dispatcher.add_handler(CommandHandler("stop", self.command_stop))
        self.dispatcher.add_handler(CommandHandler("help", self.command_help))
        self.dispatcher.add_handler(CommandHandler(["pause", "resume"], self.command_pause_resume))
        self.dispatcher.add_handler(MessageHandler(Filters.command, self.command_unknown))

        # log all errors
        self.dispatcher.add_error_handler(self.command_error)

        # TEST : unhandled messages
        self.dispatcher.add_handler(MessageHandler(Filters.text, self.echo))

    @staticmethod
    def command_unknown(_, update):
        update.message.reply_text("Unfortunately, I don't know the command: {0}".format(update.effective_message.text))

    @staticmethod
    def command_help(_, update):
        message = "My CryptoBot skills:" + TelegramApp.EOL + TelegramApp.EOL
        message += "/start: Displays my startup message." + TelegramApp.EOL
        message += "/ping: Shows for how long I'm working." + TelegramApp.EOL
        message += "/portfolio or /pf: Displays my current portfolio." + TelegramApp.EOL
        message += "/open_orders or /oo: Displays my current open orders." + TelegramApp.EOL
        message += "/trades_history or /th: Displays my trades history since I started." + TelegramApp.EOL
        message += "/profitability or /pb: Displays the profitability I made since I started." + TelegramApp.EOL
        message += "/market_status or /ms: Displays my understanding of the market and my risk parameter." + TelegramApp.EOL
        message += "/set_risk: Changes my current risk setting into your command's parameter." + TelegramApp.EOL
        message += "/stop: Stops me." + TelegramApp.EOL
        message += "/help: Displays this help."
        update.message.reply_text(message)

    @staticmethod
    def get_command_param(command_name, update):
        return update.message.text.replace(command_name, "")

    @staticmethod
    def command_start(_, update):
        update.message.reply_text("Hello, I'm CryptoBot, type /help to know my skills.")

    @staticmethod
    def command_stop(_, update):
        # TODO add confirmation
        update.message.reply_text("I'm leaving this world...")
        Commands.stop_bot(get_bot())

    def command_pause_resume(self, _, update):
        if self.paused:
            update.message.reply_text("Resuming...")
            set_enable_trading(True)
            self.paused = False
        else:
            update.message.reply_text("Pausing...")
            cancel_all_open_orders()
            set_enable_trading(True)
            self.paused = True

    @staticmethod
    def command_ping(_, update):
        update.message.reply_text("I'm alive since {0}.".format(
            datetime.datetime.fromtimestamp(get_bot().get_start_time()).strftime('%Y-%m-%d %H:%M:%S')))

    @staticmethod
    def command_risk(_, update):
        try:
            risk = float(TelegramApp.get_command_param("/set_risk", update))
            set_risk(risk)
            update.message.reply_text("New risk set successfully.")
        except Exception:
            update.message.reply_text("Failed to set new risk, please provide a number between 0 and 1.")

    @staticmethod
    def command_profitability(_, update):
        # to find profitabily bug out
        try:
            real_global_profitability, simulated_global_profitability, \
                real_percent_profitability, simulated_percent_profitability = get_global_profitability()
            profitability_string = "Real global profitability : {0} ({1:.3f}%){2}".format(
                PrettyPrinter.portfolio_profitability_pretty_print(real_global_profitability,
                                                                   None,
                                                                   get_reference_market()),
                real_percent_profitability,
                TelegramApp.EOL)
            profitability_string += "Simulated global profitability : {0} ({1:.3f}%)".format(
                PrettyPrinter.portfolio_profitability_pretty_print(simulated_global_profitability,
                                                                   None,
                                                                   get_reference_market()),
                simulated_percent_profitability)
            update.message.reply_text(profitability_string)
        except Exception as e:
            update.message.reply_text(str(e))

    @staticmethod
    def command_portfolio(_, update):
        portfolio_real_current_value, portfolio_simulated_current_value = get_portfolio_current_value()
        reference_market = get_reference_market()
        real_global_portfolio, simulated_global_portfolio = get_global_portfolio_currencies_amounts()

        portfolios_string = "Portfolio real value : {0:.7f} {1}{2}".format(portfolio_real_current_value,
                                                                           reference_market,
                                                                           TelegramApp.EOL)
        portfolios_string += "Global real portfolio : {1}{0}{1}{1}".format(
            PrettyPrinter.global_portfolio_pretty_print(real_global_portfolio),
            TelegramApp.EOL)

        portfolios_string += "Portfolio simulated value : {0:.7f} {1}{2}".format(portfolio_simulated_current_value,
                                                                                 reference_market,
                                                                                 TelegramApp.EOL)
        portfolios_string += "Global simulated portfolio : {1}{0}".format(
            PrettyPrinter.global_portfolio_pretty_print(simulated_global_portfolio),
            TelegramApp.EOL)
        update.message.reply_text(portfolios_string)

    @staticmethod
    def command_open_orders(_, update):
        portfolio_real_open_orders, portfolio_simulated_open_orders = get_open_orders()

        orders_string = "Real open orders :" + TelegramApp.EOL
        for orders in portfolio_real_open_orders:
            for order in orders:
                orders_string += PrettyPrinter.open_order_pretty_printer(order) + TelegramApp.EOL

        orders_string += TelegramApp.EOL + "Simulated open orders :" + TelegramApp.EOL
        for orders in portfolio_simulated_open_orders:
            for order in orders:
                orders_string += PrettyPrinter.open_order_pretty_printer(order) + TelegramApp.EOL

        update.message.reply_text(orders_string)

    @staticmethod
    def command_trades_history(_, update):
        real_trades_history, simulated_trades_history = get_trades_history()

        trades_history_string = "Real trades :" + TelegramApp.EOL
        for trades in real_trades_history:
            for trade in trades:
                trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + TelegramApp.EOL

        trades_history_string += TelegramApp.EOL + "Simulated trades :" + TelegramApp.EOL
        for trades in simulated_trades_history:
            for trade in trades:
                trades_history_string += PrettyPrinter.trade_pretty_printer(trade) + TelegramApp.EOL

        update.message.reply_text(trades_history_string)

    @staticmethod
    def command_market_status(_, update):
        try:
            message = "My cryptocurrencies evaluations are:" + TelegramApp.EOL + TelegramApp.EOL
            for currency_pair, currency_info in get_currencies_with_status().items():
                message += "- {0}:{1}".format(currency_pair, TelegramApp.EOL)
                for exchange_name, evaluation in currency_info.items():
                    message += "=> {0}: {1}{2}".format(exchange_name, evaluation.name, TelegramApp.EOL)
            message += "{0}My current risk is: {1}".format(TelegramApp.EOL, get_risk())
            update.message.reply_text(message)
        except Exception:
            update.message.reply_text("I'm unfortunately currently unable to show you my market evaluations, " +
                                      "please retry in a few seconds.")

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
    def enable(config, is_enabled):
        if CONFIG_INTERFACES not in config:
            config[CONFIG_INTERFACES] = {}
        if CONFIG_INTERFACES_TELEGRAM not in config[CONFIG_INTERFACES]:
            config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] = {}
        config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION] = is_enabled

    @staticmethod
    def is_enabled(config):
        return CONFIG_INTERFACES in config \
               and CONFIG_INTERFACES_TELEGRAM in config[CONFIG_INTERFACES] \
               and CONFIG_ENABLED_OPTION in config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM] \
               and config[CONFIG_INTERFACES][CONFIG_INTERFACES_TELEGRAM][CONFIG_ENABLED_OPTION]
