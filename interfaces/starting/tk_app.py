import _tkinter
import logging
import threading
from tkinter import *

from config.cst import PROJECT_NAME


class TkApp(threading.Thread):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.window = None
        self.start()

    def run(self):
        try:
            self.window = Tk()
            # window settings
            self.window.title(PROJECT_NAME + " - Launcher")
            self.window.geometry("500x430")

            # background
            background_image = PhotoImage(file="interfaces/web/assets/images/octopus.png")
            background_label = Label(self.window, image=background_image)
            background_label.place(x=0, y=0, relwidth=1, relheight=1)

            # buttons
            start_button = Button(self.window, text="Start Octobot", command=self.start_callback)
            start_button.pack()
            self.window.mainloop()

        except _tkinter.TclError as e:
            self.logger.error("Failed to start tk_app" + str(e))

    def start_callback(self):
        pass

    def stop(self):
        self.window.quit()
