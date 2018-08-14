import _tkinter
import logging
import threading
from abc import *
from tkinter import PhotoImage, Label, CENTER, Tk
from tkinter.ttk import Style

from config.cst import PROJECT_NAME


class TkApp(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.style_config = Style()
        self.style_config.theme_use('equilux')

        self.window = None
        self.window_title = f"{PROJECT_NAME}"
        self.window_background_text = ""

        self.start()

    def run(self):
        try:
            self.window = Tk()
            self.window.protocol("WM_DELETE_WINDOW", self.close_callback)
            # window settings
            self.window.title(self.window_title)
            try:
                self.window.iconbitmap('interfaces/web/static/favicon.ico')
            except Exception as e:
                self.logger.error("Failed to load tk window icon" + str(e))

            self.window.geometry("500x430")

            # background
            try:
                background_image = PhotoImage(file="interfaces/web/static/img/octobot.png")
                background_label = Label(self.window,
                                         image=background_image,
                                         text=self.window_background_text,
                                         compound=CENTER)

                background_label.place(x=0,
                                       y=0,
                                       relwidth=1,
                                       relheight=1)
            except Exception as e:
                self.logger.error("Failed to load tk window background" + str(e))

            self.create_components()

            self.start_app()

        except _tkinter.TclError as e:
            self.logger.error("Failed to start tk_app" + str(e))

    @staticmethod
    @abstractmethod
    def close_callback():
        pass

    def create_components(self):
        pass

    def start_app(self):
        self.window.mainloop()

    def stop(self):
        self.window.quit()
