import _tkinter
import logging
import threading
from abc import *
from tkinter import PhotoImage, Label, BOTTOM, Canvas, Frame, CENTER

from ttkthemes import ThemedTk

from config.cst import PROJECT_NAME

BACKGROUND_COLOR = "#464646"
WINDOW_SIZE = 600


class TkApp(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.window = None
        self.window_title = f"{PROJECT_NAME}"
        self.window_background_text = ""

        self.top_frame = None
        self.bottom_frame = None

        self.start()

    def run(self):
        try:
            self.window = ThemedTk()
            self.window.set_theme("equilux")

            # window settings
            self.window.title(self.window_title)
            self.window.protocol("WM_DELETE_WINDOW", self.close_callback)
            # self.window.configure(background=BACKGROUND_COLOR)

            try:
                self.window.iconbitmap('interfaces/web/static/favicon.ico')
            except Exception as e:
                self.logger.error("Failed to load tk window icon" + str(e))

            self.window.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")

            # background
            try:
                background_image = PhotoImage(file="interfaces/web/static/img/octobot.png")
                background_label = Label(self.window,
                                         image=background_image,
                                         text=self.window_background_text,
                                         compound=CENTER,
                                         bg=BACKGROUND_COLOR)

                background_label.place(x=0,
                                       y=0,
                                       relwidth=1,
                                       relheight=1)
            except Exception as e:
                self.logger.error("Failed to load tk window background" + str(e))

            # frames
            self.top_frame = Frame(self.window, bg=BACKGROUND_COLOR)
            self.bottom_frame = Frame(self.window, bg=BACKGROUND_COLOR)
            self.top_frame.pack(side="top", fill="y", expand=False)
            self.bottom_frame.pack(side="bottom", fill="y", expand=False)

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
