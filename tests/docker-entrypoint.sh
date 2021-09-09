#!/bin/bash

# check python libs
python -m pip freeze

# install tentacles
if ./OctoBot tentacles --install -a ; then
    echo "Tentacles successfully installed"
else
    unset TENTACLES_REPOSITORY
    export TENTACLES_URL_TAG=latest
    ./OctoBot tentacles --install -a
fi

# run tests
pytest -rw --ignore=tentacles/Trading/Exchange tests tentacles
