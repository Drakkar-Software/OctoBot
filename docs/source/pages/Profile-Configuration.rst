
OctoBot configuration is located in the **user** folder:


* **user/config.json** is the global configuration file, mostly used to setup the bot exchanges credentials, interfaces and notification settings.
* **user/profiles/** contains all the `profiles <Profiles.html>`_ created and imported in your OctoBot.


OctoBot's web interface allows to easily edit the configuration, however, it is also possible to manually edit configuration files.
Please be careful when manually editing them or OctoBot won't be able to read them and wont start.
Json file are readable and editable using any text editor.

.. code-block::

   ERROR    root <class 'Exception'>: Error when load config

This will appear when a configuration file is not a json valid file.

Profile configuration
================================

**user/config.json** is the technical configuration file of OctoBot, an example
is available `on github <https://github.com/Drakkar-Software/OctoBot/blob/master/octobot/config/default_config.json>`_.

When starting OctoBot, if the **user** folder is missing or incomplete, it will automatically be created or
completed with default values.

Strategies
--------------------

Default profiles can't be edited, you can duplicate them to be able to customize them.
On default profiles strategy and trading mode description are displayed instead of selectors to customize the profile.

.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_strategies.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_strategies.png
   :alt: profile_strategies



When the configured profile is a custom profile, it can be configured, `see custom profile page <Custom-Profile.html>`_

Specific evaluator configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some evaluators and trading modes can be configured.

If it is the case, configuration is possible through OctoBot's web interface.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/specific_eval_config.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/specific_eval_config.jpg
   :alt: evaluators_config

This edition interface is generated according to the
**NameOfTheRelatedClass_schema.json** `json schema <https://json-schema.org/understanding-json-schema/>`_ file
of the evaluator or trading mode to configure.

It is also possible to manually edit each configuration file using a text editor for JSON. When configurable,
each evaluator or trading mode has a **NameOfTheRelatedClass.json** file in **user/profiles/<profile_name>/specific_config**.


Currencies
--------------------


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_currencies.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_currencies.png
   :alt: currencies


OctoBot will trade all the cryptocurrencies listed in its configuration. To tell which cryptocurrencies to trade,
add the currency in the **crypto-currencies** section in **user/profiles/<profile_name>/profile.json**.

In order to keep OctoBot working at its full potential, we recommend to trade **between 1 and 5** different assets **not to use more than 10 to 15** different assets at the same time, depending on the size of your available funds. 

Examples:

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["BTC/USDT"],
         "enabled": true
       }
   }

OctoBot trading only Bitcoin against USDT

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["BTC/USDT"],
         "enabled": true
       },
       "Ethereum": {
         "pairs": ["ETH/USDT"],
         "enabled": false
       },
       "NEO": {
         "pairs": ["NEO/BTC", "NEO/ETH"],
         "enabled": true
       }
   }

OctoBot trading Bitcoin against USDT as well as NEO against BTC and ETH but not Ethereum against USDT because
Ethereum is disabled ("enabled": false)

Wildcard
^^^^^^^^^^^^^^^^^

To tell OctoBot to trade all BTC trading pairs (with BTC as a quote asset), use the wildcard "*" instead of a list for "pairs":

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["*"],
         "quote": "BTC"
       }
   }

A "quote" is required to specify the name of the currency to trade with.

Exchanges
--------------------------------

.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_exchanges.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_exchanges.png
   :alt: trading

Open your **user/profiles/<profile_name>/profile.json** file and edit this configuration :

.. code-block:: json

   "trader":{
     "enabled": true,
     "load-trade-history": false
   }

Enabled
^^^^^^^^^

When the **Enabled** parameter is set at **true**, OctoBot will trade using your real funds from your exchange's accounts.
When **false** OctoBot will never any create a real trade.

Load trade history
^^^^^^^^^^^^^^^^^^

When the **load-trade-history** parameter is set at **true**, OctoBot will load the account's recent trades for
the enabled traded pairs at startup. This allows to have a view on your account's trade history.
When **false**, OctoBot will only historize trades that happen after the bot startup.

Trading
--------------------------------

OctoBot can process two types of trading:


* Real trading using your exchanges' portfolio.
* Simulated trading using any imaginary portfolio.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_trading.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_trading.png
   :alt: trading

Or edit the trader key in **user/profiles/<profile_name>/profile.json** :

.. code-block:: json

   "trading":{
     "reference-market": "BTC",
     "risk": 0.8
   }

Reference-market
^^^^^^^^^^^^^^^^

The **Reference-market** parameter defines which currency OctBot should use as a reference,
this reference is used to compute profitability and the portfolio total value

Risk parameter
^^^^^^^^^^^^^^^^^^^

Any type of trading has its risk parameter. It is a parameter defining the behavior of the trader,
similarly to a real human trader.

The **Risk** parameter defines the behaviour of OctoBot in an optimism manner.

It is a value between 0 and 1:


* A low risk (closer to 0) will make OctoBot a very safe trader with few bold moves and mostly small trades. A 0 risk bot is very pessimistic (regarding its orders creation) and does not expect big market moves.
* A high risk (closer to 1) will make OctoBot a very active and heavy trader. A 1 risk bot is very optimistic (regarding its orders creation) and is expecting significative market moves.

Trader simulator
^^^^^^^^^^^^^^^^^^^

Additionally to the real trading system, a trading simulator is available in OctoBot.

`Here is the article describing the simulator feature of OctoBot <Simulator.html>`_
