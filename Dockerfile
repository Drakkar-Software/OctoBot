FROM python:3.7.7-slim-stretch AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install -U pip \
    && pip install Cython==0.29.16 \
    && pip install --prefer-binary -r requirements.txt \
    && python setup.py install

FROM python:3.7.7-slim-stretch

COPY --from=base /opt/venv /opt/venv

RUN useradd --create-home octobot
WORKDIR /home/octobot
USER octobot
COPY config /home/octobot/config

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

CMD ["./OctoBot", "-no"]
