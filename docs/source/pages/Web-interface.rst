Web interface
===============================

.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/home.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/home.jpg
   :alt: home


OctoBot provides a web interface for the following purposes:


* Checking OctoBot's status and moves
* Interacting with OctoBot
* Configure OctoBot

Web service configuration
-------------------------------

Add in **user/config.json** in the services key :

.. code-block:: json

   "web": {
        "port": 5001
   }

**Exemple:**

.. code-block:: json

   "services": {
      "a service": {

      },
      "web": {
          "port": 5022
      },
      "another service": {

      }
   }


* **port** is the port you want the web interface to be accessible from

Protect your web interface
-------------------------------

Using an authentication password
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can set a password to protect your web interface. This way you can secure the access to your OctoBot when hosting it on a cloud or just add a security layer to your setup.

**By default no password is required.**

You can activate the password authentication from the web interface configuration, it is also where you can set and change your password.

Any IP will be automatically **blocked after 10 authentication failures in a row**. IPs will remain blocked until your OctoBot restarts. If you accidentally block your IP, you can just restart your OctoBot.

How to set it up ?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Go to "Accounts" page
- Select "Interfaces" on the left menu
- Click on "********" next to "Password: "
- Override the "****" with your password
- Click on validate
- Click on "SAVE AND RESTART" red button on the left menu

You forgot your password
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you forgot your password, go to your **user/config.json** file and change:

.. code-block:: json

   "require-password": true,

into:

.. code-block:: json

   "require-password": false,

Then restart your OctoBot. This way you will be able to access your OctoBot without a password and then change it.

About the web interface authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


* OctoBot's web interface authentication works on the assumption that you are the only person being able to access your OctoBot's file system and the associated processes. This authentication can be deactivated by anyone being able to edit your **user/config.json** and restart your OctoBot process.
* Only a SHA256 hash of your password will be stored in you **user/config.json** file. This is making it impossible to go back to the original password you entered.

Blocking requests from other websites (CSRF)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can set the ``CORS_ALLOWED_ORIGINS`` environment variable before starting your OctoBot, this way only requests from the specified origin(s) will be answered to.

Examples:

* CORS_ALLOWED_ORIGINS=https://mybot.com
* CORS_ALLOWED_ORIGINS=http://localhost:5001
* CORS_ALLOWED_ORIGINS=https://mybot.com,https://myotherwebsite.com

Requests from other origins will be refused with a 400 error and the web interface will behave as if OctoBot was constantly disconnected.

By default, no request filter is set (equivalent to CORS_ALLOWED_ORIGINS=*) which might make your bot vulnerable to `Cross Site Request Forgery attacks <https://owasp.org/www-community/attacks/csrf>`_.
