import logging
import os
from tkinter.ttk import Progressbar, Label

from config.cst import PROJECT_NAME, GITHUB_RAW_CONTENT_URL, GITHUB_REPOSITORY, VERSION_DEV_PHASE, LAUNCHER_FILE
from interfaces.app_util import TkApp
from interfaces.launcher import create_environment_file

try:
    from interfaces.launcher.launcher import Launcher
except ImportError:
    # should have VERSION_DEV_PHASE
    launcher_url = f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/dev/{LAUNCHER_FILE}",
    create_environment_file(launcher_url, LAUNCHER_FILE)


class LauncherApp(TkApp):
    PROGRESS_MIN = 0
    PROGRESS_MAX = 100

    def __init__(self):
        self.window_title = f"{PROJECT_NAME} - Launcher"
        self.progress = None
        self.progress_label = None

        super().__init__()

    def create_components(self):
        # buttons
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

    @staticmethod
    def close_callback():
        os._exit(0)

    def start_app(self):
        self.window.mainloop()

    def stop(self):
        self.window.quit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='OctoBot - Launcher')
    parser.add_argument('-v', '--version', help='show OctoBot Launcher current version',
                        action='store_true')
    parser.add_argument('-u', '--update', help='update OctoBot with the latest version available',
                        action='store_true')

    parser.add_argument('-l', '--update_launcher', help='update OctoBot Launcher with the latest version available',
                        action='store_true')

    args = parser.parse_args()

    if args.version:
        print(Launcher.get_version())
    elif args.update:
        pass
    elif args.update_launcher:
        pass
    else:
        installer_app = LauncherApp()
        installer = Launcher(installer_app)
