#!/usr/bin/env bash
config_path="config"

echo **Installing dependencies...**
bash ./docs/install/linux_dependencies.sh

echo **Installing requirements...**
python3 -m pip install -r pre_requirements.txt
python3 -m pip install -r requirements.txt

echo **Installing modules...**
python3 start.py -p install all
