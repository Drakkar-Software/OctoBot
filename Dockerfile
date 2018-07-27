FROM python:3

ARG octobot_branch="beta"

LABEL octobot_version="0.1.5_3-beta"

# Update Software repository
RUN apt-get update
RUN apt install git -y

# Set up dev environment
WORKDIR /bot
RUN git clone https://github.com/Drakkar-Software/OctoBot /bot/octobot
WORKDIR /bot/octobot
RUN git checkout $octobot_branch

# install dependencies
RUN bash ./docs/install/linux_installer.sh

# clean apt
RUN rm -rf /var/lib/apt/lists/*

# configuration
RUN cp ./config/default_config.json ./config.json
RUN cp ./config/default_evaluator_config.json ./config/evaluator_config.json

# python libs
RUN pip3 install -U setuptools
RUN pip3 install -r requirements.txt

# install evaluators
RUN rm -rf ./tentacles
RUN python start.py -p install all

# copy in remote
COPY /bot/octobot OctoBot/

# entry point
ENTRYPOINT ["python"]

# entry point's default argument
CMD ["start.py"]
