FROM python:3.13-slim-bullseye AS base

WORKDIR /

# Install system dependencies for building
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git gcc binutils libffi-dev libssl-dev libxml2-dev libxslt1-dev libxslt-dev libjpeg62-turbo-dev libatlas-base-dev zlib1g-dev curl \
    && python -m venv /opt/venv

# skip cryptography rust compilation (required for armv7 builds)
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

COPY start.pex /octobot/

RUN chmod +x /octobot/start.pex

# RUN python -m venv /opt/venv \
#     && . /opt/venv/bin/activate \
#     && pip install -U pip setuptools wheel \
#     && pip install --no-cache-dir /tmp/octobot-*.whl

FROM python:3.13-slim-bullseye

ARG TENTACLES_URL_TAG=""
ENV TENTACLES_URL_TAG=$TENTACLES_URL_TAG

WORKDIR /octobot

# Import python dependencies
COPY --from=base /opt/venv /opt/venv

# Add default config files
COPY octobot/config /octobot/octobot/config

COPY docker/* /octobot/

# 1. Install requirements
# 2. Install required packages
# 3. Finish env setup
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl libxslt-dev libxcb-xinput0 libjpeg62-turbo-dev zlib1g-dev libblas-dev liblapack-dev libatlas-base-dev libopenjp2-7 libtiff-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/venv/bin/OctoBot OctoBot # Make sure we use the virtualenv \
    && chmod +x docker-entrypoint.sh

VOLUME /octobot/backtesting
VOLUME /octobot/logs
VOLUME /octobot/tentacles
VOLUME /octobot/user

EXPOSE 5001

HEALTHCHECK --interval=15s --timeout=10s --retries=5 CMD curl -sS http://127.0.0.1:5001 || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
