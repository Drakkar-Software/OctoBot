import os
from tkinter.ttk import Progressbar, Label

from config.cst import PROJECT_NAME
from interfaces.app_util import TkApp
from interfaces.launcher import launcher_controller

LAUNCHER_VERSION = "1.0.0"


class LauncherApp(TkApp):
    PROGRESS_MIN = 0
    PROGRESS_MAX = 100

    def __init__(self):
        self.window_title = f"{PROJECT_NAME} - Launcher"
        self.progress = None
        self.progress_label = None
        self.start_bot_button = None
        self.update_bot_button = None
        self.update_launcher_button = None
        self.export_logs_button = None

        super().__init__()

    def create_components(self):
        # buttons
        self.start_bot_button = Button(master, command=self.start_bot_handler, text="Start Octobot")
        self.start_bot_button.grid()

        self.update_bot_button = Button(master, command=self.update_bot_handler, text="Start Octobot")
        self.update_bot_button.grid()

        self.update_launcher_button = Button(master, command=self.update_launcher_handler, text="Start Octobot")
        self.update_launcher_button.grid()

        self.progress = Progressbar(self.window, orient="horizontal",
                                    length=200, mode="determinate")
        self.progress.pack()
        self.progress_label = Label(self.window, text=f"{self.PROGRESS_MIN}%")
        self.progress_label.pack()
        self.progress["value"] = self.PROGRESS_MIN
        self.progress["maximum"] = self.PROGRESS_MAX

    def inc_progress(self, inc_size, to_max=False):
        if to_max:
            self.progress["value"] = self.PROGRESS_MAX
            self.progress_label["text"] = f"{self.PROGRESS_MAX}%"
        else:
            self.progress["value"] += inc_size
            self.progress_label["text"] = f"{round(self.progress['value'], 2)}%"

    def update_bot_handler(self):
        self.update_bot(self)

    def update_launcher_handler(self):
        os.execl(sys.executable, os.path.abspath(__file__), ["--update_launcher"])

    def start_bot_handler(self):
        installer = launcher_controller.Launcher(self)

    @staticmethod
    def update_bot(app=None):
        launcher = launcher_controller.Launcher(app)

    @staticmethod
    def export_logs():
        pass

    @staticmethod
    def close_callback():
        os._exit(0)

    def start_app(self):
        self.window.mainloop()

    def stop(self):
        self.window.quit()
