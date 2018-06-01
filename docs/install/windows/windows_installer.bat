#!/usr/bin/env bash
@echo off
REM VARS
set bot_location="../../../"
set config_path=config
set python_cmd=python

REM dependencies url
set TA_LIB_WIN32=https://github.com/Drakkar-Software/OctoBot/releases/download/0.0.12-alpha/TA_Lib-0.4.17-cp36-cp36m-win32.whl
set TA_LIB_WIN64=https://github.com/Drakkar-Software/OctoBot/releases/download/0.0.12-alpha/TA_Lib-0.4.17-cp36-cp36m-win_amd64.whl
set TWISTED_WIN32=https://github.com/Drakkar-Software/OctoBot/releases/download/0.0.12-alpha/Twisted-18.4.0-cp36-cp36m-win32.whl
set TWISTED_WIN64=https://github.com/Drakkar-Software/OctoBot/releases/download/0.0.12-alpha/Twisted-18.4.0-cp36-cp36m-win_amd64.whl

REM TEST INSTALL
python --version 2>NUL
if errorlevel 1 goto errorNoPython

REM REQUIREMENTS
echo **Installing dependencies...**
REM ARCH AMD64
%python_cmd% -m pip install %TA_LIB_WIN64%
%python_cmd% -m pip install %TWISTED_WIN64%

REM ARCH WIN32
%python_cmd% -m pip install %TA_LIB_WIN32%
%python_cmd% -m pip install %TWISTED_WIN32%

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

REM Once done, exit the batch file -- skips executing the errorNoPython section
goto:eof

:errorNoPython
echo.
echo Error^: Python not installed (check https://github.com/Drakkar-Software/OctoBot/wiki/Installation)
