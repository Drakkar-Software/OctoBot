FROM python:3.6.6

ARG octobot_branch="dev"
ARG octobot_install_dir="Octobot"

# Update Software repository
RUN apt update
RUN apt install git -y

# Associate current user dir to octobot installation folder
ADD . /bot
WORKDIR /bot

# Set up octobot's environment
RUN git clone https://github.com/Drakkar-Software/OctoBot /bot/$octobot_install_dir
WORKDIR /bot/$octobot_install_dir
RUN git checkout $octobot_branch

# install dependencies
RUN bash ./docs/install/linux_dependencies.sh
RUN apt clean && rm -rf /var/lib/apt/lists/*

# configuration
RUN cp ./config/default_config.json ./config.json
RUN cp ./config/default_evaluator_config.json ./config/evaluator_config.json

# python libs
RUN pip3 install -U setuptools
RUN pip3 install -r pre_requirements.txt
RUN pip3 install -r requirements.txt -r dev_requirements.txt

# install evaluators
RUN rm -rf ./tentacles
RUN python start.py -p install all

ENTRYPOINT ["python", "./start.py", "-ng"]
