bot_instance = None


def __init__(bot):
    global bot_instance
    bot_instance = bot


def get_bot():
    return bot_instance

