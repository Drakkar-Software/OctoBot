# Import flask dependencies
from flask import Blueprint, render_template

# Define the blueprint: "bot"
from interfaces.web import get_bot

bot_blueprint = Blueprint('bot', __name__, url_prefix='/bot')


# Sample HTTP error handling
@bot_blueprint.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@bot_blueprint.route('/')
def home():
    exchange_trader_simulators = get_bot().get_exchange_trader_simulators()
    portfolio = exchange_trader_simulators[next(iter(exchange_trader_simulators))].get_portfolio().get_portfolio()
    return render_template("index.html", portfolio=portfolio)
