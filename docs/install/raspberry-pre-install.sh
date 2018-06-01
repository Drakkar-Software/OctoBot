#!/usr/bin/env bash
if add-apt-repository ppa:jonathonf/python-3.6; then
    echo Repository found and compatible, downloading python3.6 from there.
    apt update
    apt install -y python3 python3-pip
else
    echo Impossible to add repository to the list, probably because of a light operating system, installing python3.6 the hard way, this might take several minutes.

    echo Step 1/5 "====>" Installing dependancies
    bash ./docs/install/linux_dependencies.sh
    apt-get install -y tk-dev

    echo Step 2/5 "====>"  Downloading and preparing Python3.6 to be installed, this might take some time
    wget https://www.python.org/ftp/python/3.6.5/Python-3.6.5.tar.xz
    tar xf Python-3.6.5.tar.xz
    cd Python-3.6.5
    ./configure

    echo Step 3/5 "====>" Installing Python3.6, this takes some time
    make altinstall

    echo Step 4/5 "====>" Updating Python3.6 service_identity
    pip3.6 install service_identity --force --upgrade

    echo Step 5/5 "====>" Removing installation files
    cd ..
    rm -rf Python-3.6.5.tar.xz Python-3.6.5
fi
