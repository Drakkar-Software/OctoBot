
Tentacle Manager
================

OctBot is fully modular, so you can install any modules you want ! 


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :alt: tentacles


You can find in `this <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_ repository all default tentacles (modules) you can create to custom your own cryptocurrencies trader bot.

**It's very simple !**
If you used `OctoBot's launcher <https://github.com/Drakkar-Software/OctoBot/wiki/Installation#instructions>`_ to install OctoBot, you dont need to do this.

Otherwise, after the `developper installation <https://github.com/Drakkar-Software/OctoBot/wiki/Installation#developer-installation>`_ of your OctoBot, you just have to type : 

.. code-block::

   python start.py tentacles --install --all

And all the default tentacles package from this repository will be installed (and activated).

If you want to modify or disable some of them `see this wiki page <https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot>`_.

Add new tentacles packages to your OctoBot
------------------------------------------

Using the web interface
^^^^^^^^^^^^^^^^^^^^^^^


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles_packages.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles_packages.jpg
   :alt: tentacles_packages


Got to the **Tentacles** section on the navigation bar, then go to **INSTALL TENTACLES PACKAGES** and register the address (local or url) of the wanted tentacles packages. This will automatically install the package in your OctoBot.

Install a specific tentacle
---------------------------

*This tentacle have to be available in one of your tentacles repositories (see above).*

To install a tentacle, type: 

.. code-block::

   python start.py tentacles --install NAME_OF_YOUR_TENTACLE
