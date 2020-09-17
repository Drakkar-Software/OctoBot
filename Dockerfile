FROM python:3.7-slim-buster AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev libxslt-dev libjpeg62-turbo-dev zlib1g-dev \
    && python -m venv /opt/venv

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install --upgrade pip>=20.0.0 \
    && pip install Cython==0.29.21 \
    && pip install --extra-index-url https://www.piwheels.org/simple --extra-index-url https://www.tentacles.octobot.online/repository/octobot_pypi/simple --only-binary OctoBot-Commons --only-binary OctoBot-Channels --only-binary OctoBot-Evaluators --only-binary OctoBot-Backtesting --only-binary OctoBot-Trading --prefer-binary -r requirements.txt \
    && python setup.py install

FROM python:3.7-slim-buster

WORKDIR /octobot
COPY --from=base /opt/venv /opt/venv
COPY octobot/config /octobot/octobot/config

RUN apt-get update \
    && apt-get install -y --no-install-recommends libxslt-dev libxcb-xinput0 libjpeg62-turbo-dev zlib1g-dev libblas-dev liblapack-dev libatlas-base-dev libopenjp2-7 libtiff-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/venv/bin/OctoBot OctoBot # Make sure we use the virtualenv

VOLUME /octobot/tentacles
VOLUME /octobot/user

ENTRYPOINT ["./OctoBot"]
