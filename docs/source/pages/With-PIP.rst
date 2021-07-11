With Python index package (pip)
============================================================
Requirements
------------
* Python 3.8 (\ `download <https://www.python.org/downloads/>`_\ )
* Add python to your PATH (\ `tutorial windows <https://superuser.com/questions/143119/how-do-i-add-python-to-the-windows-path>`_\ )

Installation
------------

In a command line (with python in your PATH) type the following command : 

.. code-block::

   $ python3.8 -m pip install OctoBot>=0.4.0b

You can change **python3.8** to the name of the python binary you added to your PATH (for example on linux you may use **python3**\ )

Usage
-----

.. code-block::

   $ OctoBot


Start multiple OctoBots
---------------------------------------

To run a second OctoBot on the same computer :

1. Create a new directory and enter it

2. Start OctoBot and stop it after 1-2min to let it create default files

3. Open user/config.json file

4. Change web config lines

FROM

.. code-block:: json

        "web": {
            "auto-open-in-web-browser": true
        }

TO

.. code-block:: json

        "web": {
            "auto-open-in-web-browser": true,
            "port": 8000
        }

In this example, the second OctoBot's web interface is accessible at http://127.0.0.1:8000.

Any port can be used except those already used by another OctoBot or any software on your system.

5. Start the new OctoBot
