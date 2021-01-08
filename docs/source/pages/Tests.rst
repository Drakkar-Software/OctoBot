
Tests
=====

Requirements
------------

To run OctoBot's tests, an OctoBot development environment is necessary, development environment setup is described `here <Developer-Guide.html#environment-setup>`_

OctoBot engine
--------------

To run OctoBot's engine tests, use the *pytest tests* in OctoBot's root folder :

.. code-block:: bash

   pytest tests

This will run all tests in the test folder.

Tentacles
---------

To run OctoBot's tentacles tests, use the *pytest tentacles* command in OctoBot's root folder :

.. code-block:: bash

   pytest tentacles

This will run all tests in the **tentacles** folder.
Testing tentacles works only if tentacles are installed on the tested OctoBot. See `OctoBot's tentacle manager <Tentacle-Manager.html>`_ to install tentacles.
