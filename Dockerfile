FROM python:3.7.7-slim-stretch AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install --upgrade pip \
    && pip install Cython>=0.29.17 \
    && pip install --only-binary OctoBot-Commons --only-binary OctoBot-Channels --only-binary OctoBot-Evaluators --only-binary OctoBot-Backtesting --only-binary OctoBot-Trading --prefer-binary -r requirements.txt \
    && python setup.py install

FROM python:3.7.7-slim-stretch

WORKDIR /octobot
COPY --from=base /opt/venv /opt/venv
COPY config /octobot/config

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

RUN cp /opt/venv/bin/OctoBot /octobot/OctoBot

ENTRYPOINT ["./OctoBot"]
CMD ["-no"]
