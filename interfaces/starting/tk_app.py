import socket
import webbrowser
from time import sleep
from tkinter import *

from config.cst import PROJECT_NAME, CONFIG_CATEGORY_SERVICES, CONFIG_WEB, CONFIG_WEB_PORT
from interfaces import get_bot
from interfaces.app_util import TkApp
from tools.commands import Commands


class StartingApp(TkApp):
    def __init__(self, config):
        self.config = config

        self.window_title = f"{PROJECT_NAME} - Launcher"
        self.window_background_text = f"{PROJECT_NAME} is running"
        super().__init__()

    @staticmethod
    def close_callback():
        Commands.stop_bot(get_bot())

    def create_components(self):
        # buttons
        start_button = Button(self.window, text="Open OctoBot", command=self.start_callback)
        start_button.pack()

    def start_callback(self):
        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        webbrowser.open(f"http://{socket.gethostbyname(socket.gethostname())}:"
                        f"{self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT]}")

    def start_app(self):
        self.window.mainloop()

    def stop(self):
        self.window.quit()
