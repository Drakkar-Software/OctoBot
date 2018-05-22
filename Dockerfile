#Download base image ubuntu 16.04
FROM ubuntu:16.04

# Update Ubuntu Software repository
RUN apt-get update
RUN apt install git -y

# Set up dev environment
WORKDIR /bot
RUN git clone https://github.com/Trading-Bot/CryptoBot /bot/cryptobot
WORKDIR /bot/cryptobot
RUN git checkout dev

# install dependencies
RUN bash ./docs/install/linux_installer.sh

# configuration
RUN cp ./config/default_config.json ./config/config.json

# python libs
RUN python3 -m pip install -r requirements.txt

# install evaluators
RUN python3 start.py -p install all
