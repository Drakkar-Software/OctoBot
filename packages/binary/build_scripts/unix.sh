#!/bin/bash
python3 -m pip freeze
python3 packages/binary/scripts/python_file_lister.py bin/octobot_packages_files.txt
python3 packages/binary/scripts/insert_imports.py octobot/cli.py
python3 packages/binary/scripts/fetch_nltk_data.py words $NLTK_DATA
python3 -m PyInstaller bin/start.spec --workpath installer
./dist/OctoBot --version
mv dist/OctoBot ./OctoBot_$BUILD_ARCH && rm -rf dist/
ls -al
