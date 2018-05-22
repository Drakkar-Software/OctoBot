class PackageManager:
    def __init__(self, config):
        self.config = config

    def parse_commands(self, commands):
        if len(commands) > 0:
            if commands[0] == "install":
                pass
