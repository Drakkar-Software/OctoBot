from interfaces.starting.tk_app import StartingApp

tk_app = None


def __init__(config):
    global tk_app
    tk_app = StartingApp(config)
