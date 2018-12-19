FROM python:3.6.6

ARG OCTOBOT_REPOSITORY="https://github.com/Drakkar-Software/OctoBot"
ARG OCTOBOT_BRANCH="dev"
ARG OCTOBOT_INSTALL_DIR="octobot"

ENV TENTACLE_DIR="tentacles" \
    CONFIG_FILE="config.json"

# Update Software repository
RUN apt update
RUN apt install git -y

# Set up octobot's environment
WORKDIR /bot
RUN git clone $OCTOBOT_REPOSITORY $OCTOBOT_INSTALL_DIR -b $OCTOBOT_BRANCH
WORKDIR /bot/$OCTOBOT_INSTALL_DIR

# install dependencies
RUN bash ./docs/install/linux_dependencies.sh
RUN apt clean -yq && apt autoremove -yq && rm -rf /var/lib/apt/lists/*

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

VOLUME /bot/$OCTOBOT_INSTALL_DIR/$CONFIG_FILE
VOLUME /bot/$OCTOBOT_INSTALL_DIR/$TENTACLE_DIR

ENTRYPOINT ["python", "./start.py", "-ng"]
