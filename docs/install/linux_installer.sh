#!/usr/bin/env bash
config_path="octobot/config"

echo **Installing dependencies...**
bash ./docs/install/linux_dependencies.sh

echo **Installing requirements...**
python3 -m pip install -r pre_requirements.txt
python3 -m pip install -r requirements.txt

echo **Set default configuration...**
cd $config_path
cp default_config.json ../../config.json

echo **Installing modules...**
cd ../..
python3 start.py -p install all
