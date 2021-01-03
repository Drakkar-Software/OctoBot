
Requirements
------------


* Python 3.8 (\ `download <https://www.python.org/downloads/>`_\ )
* Git (\ `Download <https://git-scm.com/downloads>`_\ )

Instructions
------------

Windows
^^^^^^^

**Python3.8 has to be in environment variable** :

During `python install <https://www.python.org/downloads>`_ check *add to environment var* checkbox.

Open a command line and type :

.. code-block:: bash

   git clone https://github.com/Drakkar-Software/OctoBot -b dev
   cd OctoBot
   python3 -m pip install -Ur requirements.txt
   python3 start.py tentacles --install --all

There **python3** is refering to your **Python3.8.X** installation, just adapt the commands to match your setup if any different (might be python, python3, python3.8, etc: it depends on your environment).

Note that python3.8 might be available under the name **python3.8** after this installation.
