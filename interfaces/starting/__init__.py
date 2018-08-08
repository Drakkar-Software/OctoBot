from interfaces.starting.tk_app import TkApp

tk_app = None


def __init__(config):
    global tk_app
    tk_app = TkApp(config)
