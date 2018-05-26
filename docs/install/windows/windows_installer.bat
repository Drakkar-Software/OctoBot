#!/usr/bin/env bash
@echo off
REM VARS
set bot_location="../../../"
set config_path=config
set python_cmd=python

REM REQUIREMENTS
echo **Installing dependencies...**
REM ARCH AMD64
%python_cmd% -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win_amd64.whl
%python_cmd% -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win_amd64.whl

REM ARCH WIN32
%python_cmd% -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win32.whl
%python_cmd% -m pip install wheels/Twisted-18.4.0-cp36-cp36m-win32.whl

REM BOT INSTALL
cd %bot_location%

REM BOT REQUIREMENTS
echo **Installing requirements...**
%python_cmd% -m pip install -r requirements.txt

REM CONFIGURATION
echo **Set default configuration...**
cd %config_path%
copy default_config.json config.json
copy default_evaluator_config.json evaluator_config.json

REM BOT MODULES INSTALL
echo **Installing modules...**
cd ..
%python_cmd% start.py -p install all