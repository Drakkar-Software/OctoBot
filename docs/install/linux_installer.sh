#!/usr/bin/env bash
echo **Installing dependencies...**
apt install -y wget python3 python3-dev python3-pip python3-tk -y
bash ./docs/install/linux_dependencies.sh

echo **Installing requirements...**
bash ./docs/install/install-ta-lib.sh

echo **Set default configuration...**
cd %config_path%
cp default_config.json ../config.json

REM BOT MODULES INSTALL
echo **Installing modules...**
cd ..
python3 start.py -p install all
