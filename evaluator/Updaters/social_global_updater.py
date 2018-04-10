import threading


class SocialGlobalUpdaterThread(threading.Thread):
    def __init__(self, symbol_evaluator):
        super().__init__()
        self.symbol_evaluator = symbol_evaluator
        self.keep_running = True

    def run(self):
        pass
        # while self.keep_running:
        #     time.sleep(10)

    def stop(self):
        self.keep_running = False

