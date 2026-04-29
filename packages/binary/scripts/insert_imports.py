import sys


TO_INSERT_LINES = [
    "from engineio.async_drivers import gevent"  # required for pyinstaller to add gevent and be able to use it later.
]


def insert_imports(target_file):
    with open(target_file, "a") as file_append:
        file_append.writelines([f"{line}\n" for line in TO_INSERT_LINES])
        print(f"{len(TO_INSERT_LINES)} lines appended into {target_file}")


if __name__ == "__main__":
    insert_imports(sys.argv[1])
