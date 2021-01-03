
OctoBot's environment variables
===============================

Global variables
----------------

``ENV_TENTACLES_URL_TAG`` overrides the default OctoBot version tag for tentacles package installation. Some additional tags are available : 


* **latest** : for the tentacles developers
* **tests/XXX** : for OctoBot-Tentacles-Manager tests

Interfaces / Services variables
-------------------------------

Web
^^^


* ``ENV_WEB_ADDRESS`` overrides the host IP address, can be set to ``0.0.0.0`` to accept all incoming connections.
* ``ENV_WEB_PORT`` overrides the default web port (5001).
