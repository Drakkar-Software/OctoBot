#!/bin/bash
python3 -m pip install -U pip setuptools wheel
python3 -m pip install -r requirements.txt
git clone -q $OCTOBOT_GH_REPO -b $OCTOBOT_DEFAULT_BRANCH
python3 -m pip install --prefer-binary -r $OCTOBOT_REPOSITORY_DIR/dev_requirements.txt -r $OCTOBOT_REPOSITORY_DIR/requirements.txt -r $OCTOBOT_REPOSITORY_DIR/full_requirements.txt
python3 -m pip freeze
python3 scripts/python_file_lister.py bin/octobot_packages_files.txt $OCTOBOT_REPOSITORY_DIR
python3 scripts/insert_imports.py $OCTOBOT_REPOSITORY_DIR/octobot/cli.py
cp -R bin $OCTOBOT_REPOSITORY_DIR
cd $OCTOBOT_REPOSITORY_DIR
python3 ../scripts/fetch_nltk_data.py words $NLTK_DATA
python3 -m PyInstaller bin/start.spec
mv dist/OctoBot ./OctoBot_$BUILD_ARCH && rm -rf dist/
ls -al
