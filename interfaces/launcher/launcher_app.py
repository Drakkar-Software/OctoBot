import os
import subprocess
import sys
from tkinter.ttk import Progressbar, Label, Button

from config.cst import PROJECT_NAME
from interfaces.app_util import TkApp
from interfaces.launcher import launcher_controller
from interfaces.launcher.launcher_controller import Launcher

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
        self.start_bot_button = Button(self.window, command=self.start_bot_handler, text="Start Octobot")
        self.start_bot_button.pack()

        self.update_bot_button = Button(self.window, command=self.update_bot_handler, text="Update Octobot")
        self.update_bot_button.pack()

        self.progress = Progressbar(self.window, orient="horizontal",
                                    length=200, mode="determinate")
        self.progress.pack()
        self.progress_label = Label(self.window, text=f"{self.PROGRESS_MIN}%")
        self.progress_label.pack()

        self.update_launcher_button = Button(self.window, command=self.update_launcher_handler, text="Update Launcher")
        self.update_launcher_button.pack()

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
        launcher_process = subprocess.Popen([sys.executable, "--update_launcher"])

        if launcher_process:
            self.hide()
            launcher_process.wait()

            new_launcher_process = subprocess.Popen([sys.executable])

            if new_launcher_process:
                self.stop()

    def start_bot_handler(self):
        bot_process = Launcher.execute_command_on_detached_bot()

        if bot_process:
            self.hide()
            bot_process.wait()
            self.stop()

    @staticmethod
    def update_bot(app=None):
        launcher_controller.Launcher(app)

    @staticmethod
    def export_logs():
        pass

    @staticmethod
    def close_callback():
        os._exit(0)

    def start_app(self):
        self.window.mainloop()

    def hide(self):
        self.window.withdraw()

    def stop(self):
        self.window.quit()
