FROM arm32v7/python:3.7.3-slim-stretch AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install --upgrade pip \
    && pip install --prefer-binary -r requirements.txt \
    && python setup.py install

FROM arm32v7/python:3.7.3-slim-stretch

WORKDIR /octobot
COPY --from=base /opt/venv /opt/venv
COPY config /octobot/config

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

RUN cp /opt/venv/bin/OctoBot /octobot/OctoBot

CMD ["./OctoBot", "-no"]
