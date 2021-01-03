With docker
============================================================
.. WARNING:: For unix distribution only

Installing docker
-----------------

Please follow the instructions `here <https://docs.docker.com/install/linux/docker-ce/debian/>`_ for a debian computer.

For a raspberry installation please follow `this guide <https://phoenixnap.com/kb/docker-on-raspberry-pi>`_.

Running last release Octobot image
----------------------------------

For linux x64/x86 and raspberry linux arm64/arm32

.. code-block::

   docker run -itd --name Octobot -p 80:5001 drakkarsoftware/octobot:stable

Running lastest (may be unstable) Octobot image
-----------------------------------------------

For linux x64/x86 and raspberry linux arm64/arm32

.. code-block::

   docker run -itd --name Octobot -p 80:5001 drakkarsoftware/octobot:latest

Running with docker-compose
---------------------------

A simple way to run a docker image is to use docker-compose : 


* Install `docker-compose <https://docs.docker.com/compose/install/>`_
* Download the `docker-compose.yml file <https://github.com/Drakkar-Software/OctoBot/blob/master/docker-compose.yml>`_
* Start OctoBot with docker-compose : 
  .. code-block::

     docker-compose up -d

How to look at OctoBot logs ?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   docker logs Octobot -f

How to stop OctoBot ?
^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   docker stop Octobot

How to restart OctoBot ?
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   docker restart Octobot

How to update OctoBot ?
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   docker stop Octobot
   docker rm Octobot


* Then use the `pull <https://github.com/Drakkar-Software/OctoBot/wiki/With-Docker#pulling-octobot-image>`_ command above
* Then use the `run <https://github.com/Drakkar-Software/OctoBot/wiki/With-Docker#running-octobot-image>`_ command above

Pulling Octobot image
---------------------

last release image
^^^^^^^^^^^^^^^^^^

.. code-block::

   docker pull drakkarsoftware/octobot:stable

latest image
^^^^^^^^^^^^

.. code-block::

   docker pull drakkarsoftware/octobot:latest
