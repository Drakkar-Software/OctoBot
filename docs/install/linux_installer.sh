#!/usr/bin/env bash
echo **Installing dependencies...**
apt install -y wget python3 python3-dev python3-pip python3-tk -y
bash ./docs/install/linux_dependencies.sh

echo **Installing requirements...**
python3 -m pip install -r pre_requirements.txt
 ython3 -m pip install -r requirements.txt

echo **Set default configuration...**
cd %config_path%
cp default_config.json ../config.json

echo **Installing modules...**
cd ..
python3 start.py -p install all
