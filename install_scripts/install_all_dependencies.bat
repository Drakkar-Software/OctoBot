@echo off
setlocal EnableDelayedExpansion

REM Install Python dependencies from requirements files at the OctoBot repo root
REM and under OctoBot\packages (any subdirectory).
REM PKG_IGNORE_DIRS: space-separated basenames under packages\ to skip (blacklist). Default: binary
REM dev_requirements.txt under packages\ is ignored; repo root dev_requirements.txt is used.
REM One pip install with multiple -r flags.

cd /d "%~dp0.."
set "OCTOBOT_ROOT=%CD%"
set "PKG_IGNORE_DIRS=binary"

set "PY="
where python3 >nul 2>&1 && set "PY=python3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo error: neither python3 nor python found in PATH 1>&2
  exit /b 1
)

set "REQ_ALL=%TEMP%\octobot_all_req_%RANDOM%_%RANDOM%.txt"
(type nul)>"%REQ_ALL%"

if exist "%OCTOBOT_ROOT%\full_requirements.txt" >>"%REQ_ALL%" echo %OCTOBOT_ROOT%\full_requirements.txt
if exist "%OCTOBOT_ROOT%\requirements.txt" >>"%REQ_ALL%" echo %OCTOBOT_ROOT%\requirements.txt
if exist "%OCTOBOT_ROOT%\dev_requirements.txt" >>"%REQ_ALL%" echo %OCTOBOT_ROOT%\dev_requirements.txt

set "PACKAGES_DIR=%OCTOBOT_ROOT%\packages"
if exist "%PACKAGES_DIR%" (
  set "REQ_PKG=%TEMP%\octobot_pkg_!RANDOM!_!RANDOM!.txt"
  (type nul)>"!REQ_PKG!"
  set "LIST_OUT=!REQ_PKG!"
  for /r "%PACKAGES_DIR%" %%F in (full_requirements.txt) do call :append_if_not_blacklisted "%%F"
  for /r "%PACKAGES_DIR%" %%F in (requirements.txt) do call :append_if_not_blacklisted "%%F"
  sort "!REQ_PKG!" /o "!REQ_PKG!.sorted"
  type "!REQ_PKG!.sorted" >>"%REQ_ALL%"
  del "!REQ_PKG!" "!REQ_PKG!.sorted" 2>nul
  set "LIST_OUT="
)

set "REQ_PIP_FLAGS=install"
set "CNT=0"
for /f "usebackq delims=" %%F in ("%REQ_ALL%") do call :add_one_req "%%F"

if !CNT! equ 0 (
  echo Nothing to install - no requirements files found.
  del "%REQ_ALL%" 2>nul
  exit /b 0
)

echo.
echo Requirements files used ^(!CNT! total^), in pip order:
set "LI=0"
for /f "usebackq delims=" %%F in ("%REQ_ALL%") do call :log_req_line "%%F"
echo.
echo Running pip install with all -r files above.
"%PY%" -m pip !REQ_PIP_FLAGS!
set "RC=!ERRORLEVEL!"
del "%REQ_ALL%" 2>nul
exit /b !RC!

:log_req_line
if not exist "%~1" exit /b 0
set /a LI+=1
echo   !LI!. %~1
exit /b 0

:add_one_req
if not exist "%~1" exit /b 0
for %%I in ("%~1") do set "REQ_PIP_FLAGS=!REQ_PIP_FLAGS! -r %%I"
set /a CNT+=1
exit /b 0

:append_if_not_blacklisted
set "OBPATH=%~1"
for %%B in (%PKG_IGNORE_DIRS%) do call :path_under_blacklisted_pkg "%%B" && exit /b 0
>>"%LIST_OUT%" echo(!OBPATH!
exit /b 0

:path_under_blacklisted_pkg
call set "T=%%OBPATH:\packages\%~1\=%%"
if not "!T!"=="!OBPATH!" exit /b 0
exit /b 1
