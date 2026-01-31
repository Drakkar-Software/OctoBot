python -m pip install -U pip setuptools wheel
python -m pip install -r requirements.txt
git clone -q $env:OCTOBOT_GH_REPO -b $env:OCTOBOT_DEFAULT_BRANCH
python -m pip install --prefer-binary -r $env:OCTOBOT_REPOSITORY_DIR/dev_requirements.txt -r $env:OCTOBOT_REPOSITORY_DIR/requirements.txt -r $env:OCTOBOT_REPOSITORY_DIR/full_requirements.txt
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
