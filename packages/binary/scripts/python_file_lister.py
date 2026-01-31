import sys
import os
import site


INIT_FILE = "__init__.py"
HANDLED_EXT = {".py", ".pyd", ".so"}
OCTOBOT_PREFIX = "octobot"
OTHER_MODULES = ["async_channel"]


def _is_file_to_handle(entry):
    return entry.name != INIT_FILE and os.path.splitext(entry.name)[-1] in HANDLED_EXT


def _is_dir_to_handle(entry):
    return not entry.name.startswith("__")


def _explore_module(package_entry, root=""):
    print(f"Exploring {root}.{package_entry.name}")
    files = []
    for entry in os.scandir(package_entry):
        import_element = entry.name.split(".")[0]
        if entry.is_dir():
            if _is_dir_to_handle(entry):
                files = files + _explore_module(entry, f"{root}{'.' if root else ''}{import_element}")
        elif _is_file_to_handle(entry):
            files.append(f"{root}.{import_element}")
    return files


def _get_octobot_packages(packages_path):
    for entry in os.scandir(packages_path):
        if (entry.name.startswith(OCTOBOT_PREFIX) or entry.name in OTHER_MODULES) \
                and not entry.name.endswith("-info") and not entry.name.endswith(".hcl"):
            yield entry


def explore_packages(packages_paths, target_file):
    files = set()
    for packages_path in packages_paths:
        for package_entry in _get_octobot_packages(packages_path):
            files = files.union(_explore_module(package_entry, package_entry.name))
    if files:
        with open(target_file, "w+") as file_w:
            file_w.writelines(sorted([f"{f}\n" for f in files]))
            print(f"{len(files)} files saved into {target_file}")


if __name__ == "__main__":
    print(f"site.getsitepackages(): {site.getsitepackages()}")
    site_packages = [s for s in site.getsitepackages() if "site-packages" in s]
    bot_package = sys.argv[2] if len(sys.argv) > 2 else "."
    print(f"exploring {site_packages}")
    explore_packages(site_packages + [bot_package], sys.argv[1])
