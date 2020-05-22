FROM python:3.7.7-slim-stretch AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev libxslt-dev libjpeg62-turbo-dev zlib1g-dev

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install --upgrade pip \
    && pip install Cython>=0.29.17 \
    && pip install --extra-index-url https://www.tentacles.octobot.online/repository/octobot_pypi/simple --only-binary OctoBot-Commons --only-binary OctoBot-Channels --only-binary OctoBot-Evaluators --only-binary OctoBot-Backtesting --only-binary OctoBot-Trading --prefer-binary -r requirements.txt \
    && python setup.py install

FROM python:3.7.7-slim-stretch

WORKDIR /octobot
COPY --from=base /opt/venv /opt/venv
COPY octobot/config /octobot/octobot/config

# Make sure we use the virtualenv
RUN ln -s /opt/venv/bin/OctoBot OctoBot

ENTRYPOINT ["./OctoBot"]
CMD ["-no"]
