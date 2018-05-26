#!/usr/bin/env bash
REM VARS
set bot_location="../../../"

REM REQUIREMENTS
echo "Installing dependencies..."
REM ARCH AMD64
python -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win_amd64.whl
python -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win_amd64.whl

REM ARCH WIN32
python -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win32.whl
python -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win32.whl

REM BOT INSTALL
cd %bot_location%

REM BOT REQUIREMENTS
echo "Installing requirements..."
python -m pip install -r requirements.txt

REM BOT MODULES INSTALL
echo "Installing modules..."
python start.py -p install all