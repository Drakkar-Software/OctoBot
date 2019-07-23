FROM python:3.7.4-slim

ENV TENTACLE_DIR="tentacles" \
    OCTOBOT_DIR="octobot" \
    LOGS_DIR="logs" \
    USER_DIR="user" \
    BUILD_DEPS="build-essential libc6-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev" \
    LIB_DEPS="libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev" \
    APPLICATION_DEPS="libxml2-dev libxslt1-dev libxslt-dev libjpeg-dev zlib1g-dev libffi-dev"

# Set up octobot's environment
COPY . /bot/$OCTOBOT_DIR
WORKDIR /bot/$OCTOBOT_DIR

# install dependencies
RUN apt-get update \
  && apt-get install -qq -y --no-install-recommends $BUILD_DEPS $LIB_DEPS $APPLICATION_DEPS \
  && pip3 install --no-cache-dir -r pre_requirements.txt \
  && pip3 install --no-cache-dir -r requirements.txt -r dev_requirements.txt \
  && mkdir $USER_DIR \
  && mkdir $LOGS_DIR \
  && cp ./config/default_config.json ./user/config.json \
  && python start.py -p install all \
  && pytest tests/unit_tests tests/functional_tests \
  && pip3 uninstall -y -r dev_requirements.txt \
  && rm -rf $TENTACLE_DIR $LOGS_DIR $USER_DIR \
  && apt-get clean -yq \
  && apt-get autoremove -yq \
  && rm -rf /var/lib/apt/lists/*

VOLUME /bot/$OCTOBOT_DIR/$USER_DIR
VOLUME /bot/$OCTOBOT_DIR/$TENTACLE_DIR
VOLUME /bot/$OCTOBOT_DIR/$LOGS_DIR

ENV WEB_PORT=5001
EXPOSE $WEB_PORT

ENTRYPOINT ["python", "./start.py", "-no"]
