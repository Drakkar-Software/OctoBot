import logging

try:
    from interfaces.starting.tk_app import StartingApp
except ModuleNotFoundError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")
except ImportError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")

tk_app = None


def __init__(config):
    global tk_app
    tk_app = StartingApp(config)
