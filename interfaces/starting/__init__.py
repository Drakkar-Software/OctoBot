import logging

try:
    from interfaces.starting.tk_app import StartingApp

    tk_app = None


    def __init__(config):
        global tk_app
        tk_app = StartingApp(config)
except ModuleNotFoundError as e:
    logging.error(f"Can't find {e} module, impossible to display GUI")
