#!/usr/bin/env bash
if add-apt-repository ppa:jonathonf/python-3.7; then
    echo Repository found and compatible, downloading python3.7 from there.
    apt update
    apt install -y python3 python3-pip
else
    echo Impossible to add repository to the list, probably because of a light operating system, installing python3.7 the hard way, this might take several minutes.

    echo Step 1/5 "====>" Installing dependancies
    bash ./docs/install/linux_dependencies.sh
    apt-get install -y tk-dev

    echo Step 2/5 "====>"  Downloading and preparing Python3.7 to be installed, this might take some time
    wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tar.xz
    tar xf Python-3.7.2.tar.xz
    cd Python-3.7.2
    ./configure

    echo Step 3/5 "====>" Installing Python3.7, this takes some time
    make -j 4
    make altinstall

    echo Step 4/5 "====>" Updating Python3.7 service_identity
    pip3.7 install service_identity --force --upgrade

    echo Step 5/5 "====>" Removing installation files
    cd ..
    rm -rf Python-3.7.2.tar.xz Python-3.7.2
fi
