import os
import shutil
import tempfile

BACKTESTING_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def static_database_fixture_path(file_name: str) -> str:
    return os.path.join(BACKTESTING_STATIC_DIR, file_name)


def copy_static_database_fixture(file_name: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".data") as temp_file:
        temp_database_path = temp_file.name
    shutil.copy2(static_database_fixture_path(file_name), temp_database_path)
    return temp_database_path


def remove_temp_database(database_path: str) -> None:
    for suffix in ("", "-wal", "-shm"):
        path = f"{database_path}{suffix}"
        if os.path.isfile(path):
            os.remove(path)
