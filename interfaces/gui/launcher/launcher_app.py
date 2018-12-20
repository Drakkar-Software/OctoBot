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

import os
import subprocess
import sys
from threading import Thread
from time import sleep
from tkinter.dialog import Dialog, DIALOG_ICON
from tkinter.ttk import Progressbar, Label, Button

from config import PROJECT_NAME
from interfaces.gui.util.app_util import AbstractTkApp
from interfaces.gui.launcher import launcher_controller
from interfaces.gui.launcher.launcher_controller import Launcher

LAUNCHER_VERSION = "1.0.4"


class LauncherApp(AbstractTkApp):
    PROGRESS_MIN = 0
    PROGRESS_MAX = 100

    def __init__(self):
        self.window_title = f"{PROJECT_NAME} - Launcher"
        self.progress = None
        self.progress_label = None
        self.start_bot_button = None
        self.update_bot_button = None
        self.bot_version_label = None
        self.launcher_version_label = None
        self.update_launcher_button = None
        self.export_logs_button = None

        Launcher.ensure_minimum_environment()

        self.processing = False

        super().__init__()

    def create_components(self):
        # bot update
        self.update_bot_button = Button(self.top_frame, command=self.update_bot_handler,
                                        text="Install/Update Octobot", style='Bot.TButton')
        self.bot_version_label = Label(self.top_frame,
                                       text="",
                                       style='Bot.TLabel')
        self.update_bot_button.grid(row=1, column=2, padx=200, pady=5)
        self.bot_version_label.grid(row=1, column=1)
        self.update_bot_version()

        # launcher update
        self.update_launcher_button = Button(self.top_frame, command=self.update_launcher_handler,
                                             text="Update Launcher", style='Bot.TButton')
        self.launcher_version_label = Label(self.top_frame,
                                            text=f"Launcher version : {LAUNCHER_VERSION}",
                                            style='Bot.TLabel')
        self.update_launcher_button.grid(row=2, column=2, padx=200, pady=5)
        self.launcher_version_label.grid(row=2, column=1, )

        # buttons
        self.start_bot_button = Button(self.top_frame, command=self.start_bot_handler,
                                       text="Start Octobot", style='Bot.TButton')
        self.start_bot_button.grid(row=3, column=1)

        # bottom
        self.progress = Progressbar(self.bottom_frame, orient="horizontal",
                                    length=200, mode="determinate", style='Bot.Horizontal.TProgressbar')
        self.progress.grid(row=1, column=1, padx=5, pady=5)
        self.progress_label = Label(self.bottom_frame, text=f"{self.PROGRESS_MIN}%", style='Bot.TLabel')
        self.progress_label.grid(row=1, column=2, padx=5)

        self.progress["value"] = self.PROGRESS_MIN
        self.progress["maximum"] = self.PROGRESS_MAX

    def inc_progress(self, inc_size, to_min=False, to_max=False):
        if to_max:
            self.progress["value"] = self.PROGRESS_MAX
            self.progress_label["text"] = f"{self.PROGRESS_MAX}%"
        elif to_min:
            self.progress["value"] = self.PROGRESS_MIN
            self.progress_label["text"] = f"{self.PROGRESS_MIN}%"
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

    def update_bot_version(self):
        current_server_version = launcher_controller.Launcher.get_current_server_version()
        current_bot_version = launcher_controller.Launcher.get_current_bot_version()
        self.bot_version_label["text"] = f"Bot version : " \
                                         f"{current_bot_version if current_bot_version else 'Not found'}" \
                                         f" (Latest : " \
                                         f"{current_server_version if current_server_version else 'Not found'})"

    @staticmethod
    def update_bot(app=None):
        if app:
            app.processing = True
        launcher_controller.Launcher(app)
        if app:
            app.processing = False
            sleep(1)
            app.update_bot_version()

    def show_alert(self, text, strings=("OK",), title="Alert", bitmap=DIALOG_ICON, default=0):
        return Dialog(self.window, text=text, title=title, bitmap=bitmap, default=default, strings=strings)

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
