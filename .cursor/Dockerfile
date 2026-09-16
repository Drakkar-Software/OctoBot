FROM python:3.13-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        sudo \
        curl \
        ca-certificates \
        build-essential \
        gcc \
        binutils \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg62-turbo-dev \
        libopenblas-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
