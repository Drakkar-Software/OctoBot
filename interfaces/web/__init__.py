import dash

app_instance = dash.Dash(__name__)
bot_instance = None


def __init__(bot):
    global bot_instance
    bot_instance = bot


def get_bot():
    return bot_instance


def load_callbacks():
    from .controller import update_values, update_strategy_values
