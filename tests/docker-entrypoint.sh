#!/bin/bash

# install tentacles
./OctoBot tentacles --install -a

# run tests
pytest -rw tests tentacles
