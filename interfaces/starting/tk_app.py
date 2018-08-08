import _tkinter
import logging
import threading
import webbrowser
from time import sleep
from tkinter import *

from config.cst import PROJECT_NAME, CONFIG_CATEGORY_SERVICES, CONFIG_WEB, CONFIG_WEB_PORT, CONFIG_WEB_IP
from interfaces import get_bot
from tools.commands import Commands


class TkApp(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.window = None
        self.start()

    def run(self):
        try:
            self.window = Tk()
            self.window.protocol("WM_DELETE_WINDOW", self.close_callback)
            # window settings
            self.window.title(PROJECT_NAME + " - Launcher")
            try:
                self.window.iconbitmap('interfaces/web/static/favicon.ico')
            except Exception as e:
                self.logger.error("Failed to load tk window icon" + str(e))

            self.window.geometry("500x430")

            # background
            background_image = PhotoImage(file="interfaces/web/assets/images/octobot.png")
            background_label = Label(self.window, image=background_image, text="Octobot is running", compound=CENTER)
            background_label.place(x=0, y=0, relwidth=1, relheight=1)

            # buttons
            start_button = Button(self.window, text="Open OctoBot", command=self.start_callback)
            start_button.pack()
            self.window.mainloop()

        except _tkinter.TclError as e:
            self.logger.error("Failed to start tk_app" + str(e))

    @staticmethod
    def close_callback():
        Commands.stop_bot(get_bot())

    def start_callback(self):
        # wait bot is ready
        while get_bot() is None or not get_bot().is_ready():
            sleep(0.1)

        webbrowser.open(f"http://localhost:{self.config[CONFIG_CATEGORY_SERVICES][CONFIG_WEB][CONFIG_WEB_PORT]}")

    def stop(self):
        self.window.quit()
