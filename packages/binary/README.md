# OctoBot-Binary
[![Release](https://img.shields.io/github/downloads/Drakkar-Software/OctoBot-Binary/total.svg)](https://github.com/Drakkar-Software/OctoBot-Binary/releases)
[![OctoBot-Binary-CI](https://github.com/Drakkar-Software/OctoBot-Binary/workflows/OctoBot-Binary-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot-Binary/actions)

OctoBot binaries is dedicated to create and upload binaries for Windows, Linux and MacOS for each [OctoBot project](https://github.com/Drakkar-Software/OctoBot) release.

### On Windows
- Just double-click on *OctoBot_windows.exe*

### On Linux and MacOS
- Open a terminal a type the following commands :
```
$ chmod +x OctoBot_linux
$ ./OctoBot_linux
```

**Replace `OctoBot_linux` by `OctoBot_osx` on MacOS**

## Binary production steps:
1. Clone OctoBot into the octobot folder
2. Install OctoBot requirements  `python -m pip install -r octobot/requirements.txt`
3. Install pyinstaller >= 4.0 pip install  `https://github.com/pyinstaller/pyinstaller/archive/develop.zip`
4. List OctoBot modules files for pyinstaller discovery  `python scripts/python_file_lister.py "bin/octobot_packages_files.txt" <octobot repo folder>`
5. Add pyinstaller required imports  `python scripts/insert_imports.py octobot/octobot/cli.py`
6. Copy bin folder into the octobot folder
7. Go into the octobot folder
8. Compile the OctoBot project `python setup.py build_ext --inplace`
9. Call pyinstaller  `pyinstaller bin\start.spec`
10. Binary should be available in the dist folder

More information on [OctoBot wiki page](https://github.com/Drakkar-Software/OctoBot/wiki/Installation).
