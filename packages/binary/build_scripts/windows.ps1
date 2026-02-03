python -m pip freeze
python packages/binary/scripts/python_file_lister.py bin/octobot_packages_files.txt
python packages/binary/scripts/insert_imports.py octobot/cli.py
python packages/binary/scripts/fetch_nltk_data.py words $env:NLTK_DATA
python -m PyInstaller bin/start.spec --workpath installer
Rename-Item dist/OctoBot.exe OctoBot_windows.exe
Copy-Item dist/OctoBot_windows.exe OctoBot_windows.exe
dist/OctoBot_windows.exe --version
