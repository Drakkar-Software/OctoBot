FROM python:3.6.6

ARG OCTOBOT_REPOSITORY="https://github.com/Drakkar-Software/OctoBot"
ARG OCTOBOT_BRANCH="dev"
ARG OCTOBOT_INSTALL_DIR="Octobot"

# Update Software repository
RUN apt update
RUN apt install git -y

# Associate current user dir to octobot installation folder
ADD . /bot
WORKDIR /bot

# Set up octobot's environment
RUN git clone $OCTOBOT_REPOSITORY /bot/$OCTOBOT_INSTALL_DIR -b $OCTOBOT_BRANCH
WORKDIR /bot/$OCTOBOT_INSTALL_DIR

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
RUN python start.py -p install all

# tests
RUN pytest tests/unit_tests tests/functional_tests

# clean up image
RUN rm -rf ./tentacles
RUN rm config.json

ENTRYPOINT ["python", "./start.py", "--docker", "-ng"]
