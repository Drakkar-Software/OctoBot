import os
import subprocess
import sys
from threading import Thread
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

        self.processing = None

        super().__init__()

    def create_components(self):
        # buttons
        self.start_bot_button = Button(self.top_frame, command=self.start_bot_handler,
                                       text="Start Octobot", style='Bot.TButton')
        self.start_bot_button.grid(row=1, column=2, padx=15)

        self.update_bot_button = Button(self.top_frame, command=self.update_bot_handler,
                                        text="Update Octobot", style='Bot.TButton')
        self.update_bot_button.grid(row=1, column=1, padx=15)

        self.update_launcher_button = Button(self.top_frame, command=self.update_launcher_handler,
                                             text="Update Launcher", style='Bot.TButton')
        self.update_launcher_button.grid(row=1, column=3, padx=15)

        self.progress = Progressbar(self.bottom_frame, orient="horizontal",
                                    length=200, mode="determinate", style='Bot.Horizontal.TProgressbar')
        self.progress.grid(row=1, column=1, padx=5)
        self.progress_label = Label(self.bottom_frame, text=f"{self.PROGRESS_MIN}%", style='Bot.TLabel')
        self.progress_label.grid(row=1, column=2, padx=5)

        self.progress["value"] = self.PROGRESS_MIN
        self.progress["maximum"] = self.PROGRESS_MAX

    def inc_progress(self, inc_size, to_max=False):
        if to_max:
            self.progress["value"] = self.PROGRESS_MAX
            self.progress_label["text"] = f"{self.PROGRESS_MAX}%"
        else:
            self.progress["value"] += inc_size
            self.progress_label["text"] = f"{round(self.progress['value'], 1)}%"

    def update_bot_handler(self):
        if not self.processing:
            thread = Thread(target=self.update_bot, args=(self,))
            thread.start()

    def update_launcher_handler(self):
        if not self.processing:
            launcher_process = subprocess.Popen([sys.executable, "--update_launcher"])

            if launcher_process:
                self.hide()
                launcher_process.wait()

                new_launcher_process = subprocess.Popen([sys.executable])

                if new_launcher_process:
                    self.stop()

    def start_bot_handler(self):
        if not self.processing:
            bot_process = Launcher.execute_command_on_detached_bot()

            if bot_process:
                self.hide()
                bot_process.wait()
                self.stop()

    @staticmethod
    def update_bot(app=None):
        if app:
            app.processing = True
        launcher_controller.Launcher(app)
        if app:
            app.processing = False

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
