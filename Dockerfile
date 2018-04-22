#Download base image ubuntu 16.04
FROM ubuntu:16.04

# Update Ubuntu Software repository
RUN apt-get update

RUN bash ./docs/install/install-ta-lib.sh

RUN cp ./docs/install/config_test.json ./config/config.json

RUN python3 -m pip install -r requirements.txt