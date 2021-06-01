With Python only
===============================

Requirements
-------------------------------
* Packages installed : Python3.8.X, Python3.8.X-dev, Python3.8.X-pip, git

Installation
-------------------------------
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

On Unix systems

.. code-block:: bash

   $ cd OctoBot
   $ python3 -m pip install -Ur requirements.txt
   $ export TENTACLES_URL_TAG="latest"
   $ python3 start.py tentacles --install --all

On Windows systems

.. code-block:: bash

   $ cd OctoBot
   $ python3 -m pip install -Ur requirements.txt
   $ SET TENTACLES_URL_TAG=latest
   $ python3 start.py tentacles --install --all

Usage
-----

The following command replaces *OctoBot Launcher*\ :

.. code-block:: bash

   $ python3 start.py

Python3
-------

There **python3** is refering to your **Python3.8.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.8, etc: it depends on your environment).

Start in background
---------------------------
.. WARNING:: For unix distribution only

With the Linux screen command, you can push running terminal applications to the background and pull them forward when you want to see them.

.. code-block:: bash

   $ sudo apt-get install -y screen
   $ screen python3 start.py


You need the number from the start of the window name to reattach it. If you forget it, you can always use the -ls (list) option, as shown below, to get a list of the detached windows:

.. code-block:: bash

   $ screen -ls
   $ screen -r 23167

(23167 is an example value)

OctoBot has been working away in the background is now brought back to your terminal window as if it had never left.
