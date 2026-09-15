import os

BACKTESTING_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def static_database_fixture_path(file_name: str) -> str:
    return os.path.join(BACKTESTING_STATIC_DIR, file_name)
