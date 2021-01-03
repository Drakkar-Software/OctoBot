
Update OctoBot with python only when using OctoBot code directly from dev branch
================================================================================

Requirements
------------


* **Python3.8.X**\ , **git** and an installed and **functional OctoBot setup** cloned from `OctoBot github repository <https://github.com/Drakkar-Software/OctoBot>`_

#
=

.. code-block:: bash

   $ git pull origin dev
   $ python3 -m pip install -Ur requirements.txt
   $ python3 start.py tentacles --install --all

Python3
-------

There **python3** is refering to your **Python3.8.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.8, etc: it depends on your environment).
