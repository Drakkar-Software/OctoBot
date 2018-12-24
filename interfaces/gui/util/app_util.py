#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import _tkinter
import logging
import os
import threading
import tkinter
from abc import *
from tkinter import PhotoImage, CENTER, Tk
from tkinter.ttk import Style, Frame

from config import PROJECT_NAME

BACKGROUND_COLOR = "#464646"
FOREGROUND_COLOR = "#a6a6a6"
PROGRESS_BAR_COLOR = "#0067F8"
ACTIVE_COLOR = "#414141"
FOCUS_COLOR = "#bebebe"
BUTTON_TEXT_COLOR = "black" if os.name == 'nt' else "white"
WINDOW_SIZE_WIDTH = 700
WINDOW_SIZE_HEIGHT = 700


class AbstractTkApp(threading.Thread):
    __metaclass__ = ABCMeta

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.window = None
        self.window_title = f"{PROJECT_NAME}"
        self.window_background_text = ""

        self.style = None

        self.top_frame = None
        self.bottom_frame = None

        self.start()

    def run(self):
        try:
            self.window = Tk()

            # set style
            self.style = Style()
            self.style.configure('Bot.TButton',
                                 background=BACKGROUND_COLOR,
                                 foreground=BUTTON_TEXT_COLOR)
            self.style.map('Bot.TButton',
                           background=[('active', ACTIVE_COLOR)],
                           relief=[('pressed', '!disabled', 'sunken')])
            self.style.configure('Bot.TFrame', background=BACKGROUND_COLOR)
            self.style.configure('Bot.TLabel',
                                 background=BACKGROUND_COLOR,
                                 foreground="white")
            self.style.configure('Bot.Horizontal.TProgressbar',
                                 foreground=PROGRESS_BAR_COLOR,
                                 background=PROGRESS_BAR_COLOR)

            # window settings
            self.window.title(self.window_title)
            self.window.protocol("WM_DELETE_WINDOW", self.close_callback)
            # self.window.configure(background=BACKGROUND_COLOR)

            try:
                self.window.iconbitmap('interfaces/web/static/favicon.ico')
            except Exception as e:
                self.logger.error("Failed to load tk window icon" + str(e))

            self.window.geometry(f"{WINDOW_SIZE_WIDTH}x{WINDOW_SIZE_HEIGHT}")

            # background
            try:
                background_image = PhotoImage(file="interfaces/web/static/img/octobot.png")
                background_label = tkinter.Label(self.window,
                                                 image=background_image,
                                                 text=self.window_background_text,
                                                 compound=CENTER,
                                                 background=BACKGROUND_COLOR)

                background_label.place(x=0,
                                       y=0,
                                       relwidth=1,
                                       relheight=1)
            except Exception as e:
                self.logger.error("Failed to load tk window background" + str(e))

            # frames
            self.top_frame = Frame(self.window, style='Bot.TFrame')
            self.bottom_frame = Frame(self.window, style='Bot.TFrame')
            self.top_frame.pack(side="top", fill="y", expand=False)
            self.bottom_frame.pack(side="bottom", fill="y", expand=False)

            self.create_components()

            self.start_app()

        except _tkinter.TclError as e:
            self.logger.exception(f"Failed to start tk_app : {e}")

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
