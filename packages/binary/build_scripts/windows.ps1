python -m pip install -U pip setuptools wheel
pants package :OctoBot
python -m pip install dist/octobot-*.whl
python -m pip freeze
python scripts/python_file_lister.py bin/octobot_packages_files.txt $env:OCTOBOT_REPOSITORY_DIR
python scripts/insert_imports.py $env:OCTOBOT_REPOSITORY_DIR/octobot/cli.py
Copy-Item bin $env:OCTOBOT_REPOSITORY_DIR -recurse
cd $env:OCTOBOT_REPOSITORY_DIR
python ../scripts/fetch_nltk_data.py words $env:NLTK_DATA
python -m PyInstaller bin/start.spec
Rename-Item dist/OctoBot.exe OctoBot_windows.exe
Copy-Item dist/OctoBot_windows.exe OctoBot_windows.exe
dist/OctoBot_windows.exe --version
