import logging
from tkinter.ttk import Progressbar

from config.cst import PROJECT_NAME
from interfaces.app_util import TkApp
from interfaces.installer.installer import Installer


class InstallerApp(TkApp):
    PROGRESS_MIN = 0
    PROGRESS_MAX = 100

    def __init__(self):
        self.window_title = f"{PROJECT_NAME} - Installer"
        self.progress = None

        super().__init__()

    def create_components(self):
        # buttons
        self.progress = Progressbar(self.window, orient="horizontal",
                                    length=200, mode="determinate")
        self.progress.pack()
        self.progress["value"] = self.PROGRESS_MIN
        self.progress["maximum"] = self.PROGRESS_MAX

    def inc_progress(self, inc_size, to_max=False):
        if to_max:
            self.progress["value"] = self.PROGRESS_MAX
        else:
            self.progress["value"] += inc_size

    @staticmethod
    def close_callback():
        pass

    def start_app(self):
        self.window.mainloop()

    def stop(self):
        self.window.quit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    installer_app = InstallerApp()
    installer = Installer(installer_app)
