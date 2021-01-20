With Python only
============================================================

Requirements
------------
* Packages installed : Python3.8.X, Python3.8.X-dev, Python3.8.X-pip, git

Installation
------------
**First, make sure you have python3.8 and python3.8-dev and python3.8-pip installed on your computer.**

Using the current stable version (master branch)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**This is the recommended python installation.**

Clone the OctoBot repository

.. code-block:: bash

   $ git clone https://github.com/Drakkar-Software/OctoBot

Install python packages :

.. code-block:: bash

   $ cd OctoBot
   $ python3 -m pip install -Ur requirements.txt
   $ python3 start.py tentacles --install --all

Using the latest version (dev branch)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
**This is installation allows to use the most up-to-date version of OctoBot but might broken depending
on the moment it is being done (modules updates might be in progress in this branch).**


Clone the OctoBot repository using the **dev** branch

.. code-block:: bash

   $ git clone https://github.com/Drakkar-Software/OctoBot -b dev

*Or if you already have an OctoBot repository*

.. code-block:: bash

   $ git checkout dev
   $ git pull

Install python packages :

.. code-block:: bash

   $ cd OctoBot
   $ python3 -m pip install -Ur requirements.txt
   $ export TENTACLES_URL_TAG="latest"
   $ python3 start.py tentacles --install --all

Usage
-----

The following command replaces *OctoBot Launcher*\ :

.. code-block:: bash

   $ python3 start.py

Python3
-------

There **python3** is refering to your **Python3.8.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.8, etc: it depends on your environment).
