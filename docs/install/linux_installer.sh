#!/usr/bin/env bash
apt install -y python3 python3-dev python3-pip python3-tk -y
bash ./docs/install/linux_dependencies.sh
bash ./docs/install/install-ta-lib.sh
bash ./docs/install/install-matplotlib.sh
