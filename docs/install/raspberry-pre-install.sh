#!/usr/bin/env bash
sudo apt-get install -y build-essential libc6-dev
sudo apt-get install -y libncurses5-dev libncursesw5-dev libreadline6-dev
sudo apt-get install -y libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev
sudo apt-get install -y libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev

sudo add-apt-repository ppa:jonathonf/python-3.6
sudo apt update
sudo apt install -y python3 python3-pip python-tk