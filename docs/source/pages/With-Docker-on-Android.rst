With Docker on Android
===============================
.. WARNING:: Experimental installation

Install Termux
-------------------------------

- Install `Termux <https://termux.com/>`_ from `Google play store <https://play.google.com/store/apps/details?id=com.termux>`_ or from `F-Droid <https://f-droid.org/en/packages/com.termux/>`_.
- Open Termux when installed

Installing alpine on Termux
-------------------------------

Run the following command to create an alpine file system on Termux

.. code-block:: bash

    curl -LO https://raw.githubusercontent.com/Hax4us/TermuxAlpine/master/TermuxAlpine.sh
    bash TermuxAlpine.sh
    startalpine

Installing udocker
-------------------------------

Install udocker to run OctoBot's docker container on alpine without root

.. code-block:: bash

    apk update
    apk add python3 curl wget
    wget https://github.com/indigo-dc/udocker/releases/download/devel3_1.2.7/udocker-1.2.7.tar.gz
    tar zxvf udocker-1.2.7.tar.gz
    export PATH=`pwd`/udocker:$PATH
    sed -i 's/env python/env python3/g'
    alias udocker="udocker --allow-root"
    udocker install

Running stable OctoBot
-------------------------------

Start OctoBot container

.. code-block:: bash

   docker run --name OctoBot -p 88888:5001 -v `pwd`/user:/octobot/user -v `pwd`/tentacles:/octobot/tentacles -v `pwd`/logs:/octobot/logs drakkarsoftware/octobot:stable

.. WARNING:: Stable is not currently supporting arm64 needed to run octobot container on Android, the latest compatible container tag is 0.4.0beta2 (drakkarsoftware/octobot:0.4.0beta2).

Open http://127.0.0.1:88888 with your phone browser to open OctoBot's web interface.
