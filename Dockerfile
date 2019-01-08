FROM python:3.7.2-slim-stretch

ARG OCTOBOT_INSTALL_DIR="octobot"

ENV TENTACLE_DIR="tentacles" \
    CONFIG_FILE="config.json" \
    LOGS_DIR="logs"

# Set up octobot's environment
COPY . /bot/$OCTOBOT_INSTALL_DIR
WORKDIR /bot/$OCTOBOT_INSTALL_DIR

# install dependencies
RUN apt update
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
RUN mkdir $LOGS_DIR
RUN python start.py -p install all

# tests
RUN pytest tests/unit_tests tests/functional_tests

# clean up image
RUN rm -rf $TENTACLE_DIR
RUN rm -rf $LOGS_DIR
RUN rm $CONFIG_FILE

VOLUME /bot/$OCTOBOT_INSTALL_DIR/$CONFIG_FILE
VOLUME /bot/$OCTOBOT_INSTALL_DIR/$TENTACLE_DIR
VOLUME /bot/$OCTOBOT_INSTALL_DIR/$LOGS_DIR

ENTRYPOINT ["python", "./start.py", "-ng"]
