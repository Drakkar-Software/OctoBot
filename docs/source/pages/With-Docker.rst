With Docker
===========
.. WARNING:: For unix distribution only

Installing docker
-----------------

Please follow the instructions `here <https://docs.docker.com/install/linux/docker-ce/debian/>`_ for a debian computer.

For a raspberry installation please follow `this guide <https://phoenixnap.com/kb/docker-on-raspberry-pi>`_.

Running stable OctoBot
----------------------

1. Download OctoBot stable

.. code-block:: bash

   docker pull drakkarsoftware/octobot:stable

2. Start OctoBot (for linux x64/x86 and raspberry linux arm64/arm32)

.. code-block:: bash

   docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:stable

Running latest OctoBot image build (may be unstable)
----------------------------------------------------

1. Download OctoBot latest

.. code-block:: bash

   docker pull drakkarsoftware/octobot:latest

2. Start OctoBot (for linux x64/x86 and raspberry linux arm64/arm32)

.. code-block:: bash

   docker run -itd --name OctoBot -p 80:5001 -v $(pwd)/user:/octobot/user -v $(pwd)/tentacles:/octobot/tentacles -v $(pwd)/logs:/octobot/logs drakkarsoftware/octobot:latest

How to look at OctoBot logs ?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker logs OctoBot -f

How to stop OctoBot ?
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker stop OctoBot

How to restart OctoBot ?
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker restart OctoBot

How to update OctoBot ?
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker stop OctoBot
   docker rm OctoBot

Running with docker-compose
---------------------------

A simple way to run a docker image is to use docker-compose : 


* Install `docker-compose <https://docs.docker.com/compose/install/>`_
* Download the `docker-compose.yml file <https://github.com/Drakkar-Software/OctoBot/blob/master/docker-compose.yml>`_
* Start OctoBot with docker-compose (with the previous file `docker-compose.yml` in the current folder) :

  .. code-block:: bash

     docker-compose up -d

Start OctoBot with docker managed files
---------------------------------------
.. WARNING:: It's easier to use but it will not be possible to update it without deleting its files.

-v arguments can be removed from previous start commands but OctoBot's local files will then be managed by docker (and not directly visible).

.. code-block:: bash

   docker run -itd --name OctoBot -p 80:5001 drakkarsoftware/octobot:stable

Local OctoBot files path are located in /var/lib/docker and can be listed with the following command

.. code-block:: bash

   docker inspect -f '{{ .Mounts }}' OctoBot

To copy files of a directory outside the OctoBot container, for example for logs files :

.. code-block:: bash

   docker cp OctoBot:/octobot/logs/. .

Wherer "OctoBot" is your container name
