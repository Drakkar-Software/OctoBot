#!/usr/bin/env bash
BUILD_DEPS="build-essential libc6-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev"
APPLICATION_DEPS="libxml2-dev libxslt1-dev libxslt-dev libjpeg-dev zlib1g-dev libffi-dev"
PYTHON_DEPS="wget python3 python3-dev python3-pip"
ADDITIONAL_DEPS="git"

apt update && apt install -qq -y $BUILD_DEPS $APPLICATION_DEPS $PYTHON_DEPS $ADDITIONAL_DEPS
