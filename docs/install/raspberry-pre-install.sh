#!/usr/bin/env bash
sudo apt update
sudo apt install -y build-essential libc6-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libxml2-dev libxslt1-dev libxslt-dev libjpeg-dev zlib1g-dev libpng12-dev libffi-dev

sudo add-apt-repository ppa:jonathonf/python-3.6
sudo apt update
sudo apt install -y python3 python3-pip python-tk