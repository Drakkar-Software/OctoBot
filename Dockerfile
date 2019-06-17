FROM python:3.7.3-slim-stretch

ARG OCTOBOT_INSTALL_DIR="octobot"

ENV TENTACLE_DIR="tentacles" \
    CONFIG_FILE="config.json" \
    LOGS_DIR="logs" \
    BUILD_DEPS="build-essential libc6-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev" \
    LIB_DEPS="libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev" \
    APPLICATION_DEPS="libxml2-dev libxslt1-dev libxslt-dev libjpeg-dev zlib1g-dev libffi-dev" \
    ADDITIONAL_DEPS="git"

# Set up octobot's environment
COPY . /bot/$OCTOBOT_INSTALL_DIR
WORKDIR /bot/$OCTOBOT_INSTALL_DIR

# install dependencies
RUN apt-get update \
  && apt-get install -qq -y --no-install-recommends $BUILD_DEPS $LIB_DEPS $APPLICATION_DEPS $ADDITIONAL_DEPS \
  && apt-get clean -yq \
  && apt-get autoremove -yq \
  && rm -rf /var/lib/apt/lists/*

# configuration and installation
RUN cp ./config/default_config.json ./config.json \
  && cp ./config/default_evaluator_config.json ./config/evaluator_config.json \
  && pip3 install -r pre_requirements.txt \
  && pip3 install -r requirements.txt -r dev_requirements.txt \
  && mkdir $LOGS_DIR \
  && python start.py -p install all

# tests
RUN pytest tests/unit_tests tests/functional_tests

# clean up image
RUN rm -rf $TENTACLE_DIR $LOGS_DIR $CONFIG_FILE \
  && apt-get remove -y $ADDITIONAL_DEPS

VOLUME /bot/$OCTOBOT_INSTALL_DIR/$CONFIG_FILE
VOLUME /bot/$OCTOBOT_INSTALL_DIR/$TENTACLE_DIR
VOLUME /bot/$OCTOBOT_INSTALL_DIR/$LOGS_DIR

EXPOSE 5001

ENTRYPOINT ["python", "./start.py", "-no"]
