import logging

try:
    from interfaces.gui.main.main_app import MainApp
except ModuleNotFoundError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")
except ImportError as e:
    logging.error(f"Can't find {e}, impossible to load GUI")

main_app = None


def __init__(config):
    global main_app
    main_app = MainApp(config)
