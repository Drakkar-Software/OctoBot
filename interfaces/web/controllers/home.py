from flask import render_template

from interfaces.web import server_instance
from interfaces.web.models.configuration import get_in_backtesting_mode
from interfaces.web.models.interface_settings import get_watched_symbols


@server_instance.route("/")
@server_instance.route("/home")
def home():
    in_backtesting = get_in_backtesting_mode()
    return render_template('index.html',
                           watched_symbols=get_watched_symbols(),
                           backtesting_mode=in_backtesting)
