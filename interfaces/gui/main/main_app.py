import socket
import webbrowser
from time import sleep
from tkinter.ttk import Button

from config.cst import PROJECT_NAME, CONFIG_CATEGORY_SERVICES, CONFIG_WEB, CONFIG_WEB_PORT
from interfaces import get_bot
from interfaces.gui.util.app_util import AbstractTkApp
from tools.commands import Commands


class MainApp(AbstractTkApp):
    def __init__(self, config):
        self.config = config

        self.window_title = f"{PROJECT_NAME} - Launcher"
        self.window_background_text = f"{PROJECT_NAME} is running"

        self.start_button = None

        super().__init__()

    @staticmethod
    def close_callback():
        Commands.stop_bot(get_bot())

    def create_components(self):
        # buttons
        self.start_button = Button(self.top_frame, command=self.start_callback, text="Open OctoBot", style='Bot.TButton')
        self.start_button.grid(row=1, column=1)

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
