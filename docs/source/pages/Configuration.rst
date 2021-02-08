
OctoBot configuration is located in two files:


* **user/config.json** is the global configuration file, mostly used to setup the bot exchanges credentials, cryptocurrency pairs, interfaces and the trading risk
* **tentacles/Evaluator/evaluator_config.json** defines the evaluators and strategies toolkit that the bot is allowed to use. This file is automatically pre-filled when `installing tentacles <Tentacle-Manager.html>`_ with OctoBot and when using the configuration web interface.
* **tentacles/Trading/trading_config.json** defines the trade mode that the bot will use. This file is automatically pre-filled when `installing tentacles <Tentacle-Manager.html>`_ with OctoBot and when using the configuration web interface.

OctoBot's web interface allows to easily edit the configuration, however, it is also possible to manually edit configuration files. Please be careful when manually editing them or OctoBot won't be able to read them and wont start. Json file are readable and editable using any text editor.

.. code-block::

   ERROR    root <class 'Exception'>: Error when load config

This will appear when a configuration file is not a json valid file.

Global configuration
====================

**user/config.json** is the technical configuration file of OctoBot, an example is available in **config/default_config.json**. 

To start with OctoBot, use **default_config.json** as an example for your **user/config.json** (copy **default_config.json** into OctoBot's **root folder/user** and rename the copy into **config.json**\ ). This operation is automatically done when using `OctoBot's installation procedure <../index.html>`_.

Exchanges
---------


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/exchanges.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/exchanges.jpg
   :alt: exchanges

Once you have your own **user/config.json** file, to start using OctoBot, you will just need to add your exchange credentials. 

.. code-block:: json

   "exchanges": {
       "EXCHANGE_NAME": {
         "api-key": "",
         "api-secret": "",
         "web-socket": true
       }
   }

`Here are the docs helping to setup an exchange for OctoBot <Exchanges.html>`_

CryptoCurrencies
----------------


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/currencies.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/currencies.jpg
   :alt: currencies


OctoBot will trade all the cryptocurrencies listed in its configuration. To tell which cryptocurrencies to trade, add the currency in the **crypto-currencies** section in **user/config.json**. 

In order to keep OctoBot working at its full potential, we recommend to trade **between 1 and 5** different assets **not to use more than 10 to 15** different assets at the same time, depending on the size of your available funds. 

Examples:

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["BTC/USDT"]
       }
   }

OctoBot trading only Bitcoin against USDT

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["BTC/USDT"]
       },
       "Ethereum": {
         "pairs": ["ETH/USDT"]
       },
       "NEO": {
         "pairs": ["NEO/BTC", "NEO/ETH"]
       }
   }

OctoBot trading Bitcoin and Ethereum against USDT as well as NEO against BTC and ETH

Wildcard
^^^^^^^^

To tell OctoBot to trade all BTC trading pairs (with BTC as a quote asset), use the wildcard "*" instead of a list for "pairs":

.. code-block:: json

   "crypto-currencies":{
       "Bitcoin": {
         "pairs": ["*"],
         "quote": "BTC"
       }
   }

A "quote" is required to specify the name of the currency to trade with.

Interfaces
----------


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/services.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/services.jpg
   :alt: services


Interfaces are all defined in **user/config.json** in the **services** section.

More details details on how to setup OctoBot's interfaces in the Interfaces section.

Trading and Risk parameter
--------------------------

OctoBot can process two types of trading:


* Real trading using your exchanges' portfolio.
  `Here are the details on how to setup a trader. <Trader.html>`_
* Simulated trading using any imaginary portfolio.
  `Here are the details on how to setup a trader simulator. <Simulator.html>`_


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :alt: trading


Any type of trading has its **risk** parameter. It is a parameter defining the behavior of the trader, similarly to a real human trader. `This risk parameter is described here <Trader.html#risk>`_

Evaluator and trading configuration
===================================


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading_modes.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading_modes.jpg
   :alt: trading_modes


**tentacles/Evaluator/evaluator_config.json** and **tentacles/Trading/trading_config.json** are configuration files telling OctoBot which evaluators, strategies and trading modes to use. It is automatically kept updated after each `Tentacle Manager <Tentacle-Manager.html>`_ usage.

An example of **tentacles/Evaluator/evaluator_config.json** is available in the **config** folder: **config/default_evaluator_config.json**.

When using OctoBot's `Tentacle Manager <Tentacle-Manager.html>`_\ , **default_evaluator_config.json** is automatically used to enable default evaluators configuration when no configuration is already available for a given evaluator. The same process is used for trading_config.

By default, new evaluatuators are not used (set to "false") if not defined otherwise in **config/default_evaluator_config.json**.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/evaluators.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/evaluators.jpg
   :alt: evaluators


Example of **evaluator_config.json**\ :

.. code-block:: json

   {
     "RSIMomentumEvaluator": true,
     "DoubleMovingAverageTrendEvaluator": true,
     "BBMomentumEvaluator": true,
     "MACDMomentumEvaluator": true,
     "CandlePatternMomentumEvaluator": false,
     "ADXMomentumEvaluator": true,


     "InstantFluctuationsEvaluator": true,


     "TwitterNewsEvaluator": true,
     "RedditForumEvaluator": false,
     "GoogleTrendStatsEvaluator": true,


     "TempFullMixedStrategiesEvaluator": true,
     "InstantSocialReactionMixedStrategiesEvaluator": false
   }


* Here, the first part is about technical analysis evaluators: they are all activated except for the **CandlePatternMomentumEvaluator**. This means that any technical evaluator of these types (except **CandlePatternMomentumEvaluator**\ ) will be used by OctoBot. 
* Second part contains only **InstantFluctuationsEvaluator**\ , OctoBot will then take real time market moves into account using **InstantFluctuationsEvaluator** only.
* Third part is the social evaluation. Here OctoBot will look at Twitter using **TwitterNewsEvaluator** (this requires that the `Twitter interface <Twitter-interface.html>`_ is setup correctly) and google stats using **GoogleTrendStatsEvaluator**. However, OctoBot will not look a reddit (\ ``"RedditForumEvaluator": false``\ ), therefore a `Reddit interface <Reddit-interface.html>`_ configuration is not necessary.
* Last part are the strategies to use. Here only one strategy out of two is to be used by OctoBot: **TempFullMixedStrategiesEvaluator**.

Any setting also applies to subclasses of these evaluators. For example if you add an evaluator extending **ADXMomentumEvaluator**\ , ``"ADXMomentumEvaluator": true`` will tell OctoBot to use the **most advanced ADXMomentumEvaluator** available: if you evaluator extends **ADXMomentumEvaluator**\ , your evaluator will be considered more advanced than the **basic ADXMomentumEvaluator** and OctoBot will use it. See the  `Customize your OctoBot page <Customize-your-OctoBot.html>`_ to learn how to add elements to your OctoBot.

This is valid for any evaluator and strategy.

Please note that any evaluator or strategy that doesn't extend an element in **evaluator_config.json** has to be added to this file otherwise will be ignored by OctoBot.

Specific evaluator configuration
================================

Some evaluators and trading modes can be configured.

If it is the case, configuration is possible through OctoBot's web interface.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/specific_eval_config.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/specific_eval_config.jpg
   :alt: evaluators_config

This edition interface is generated according to the **NameOfTheRelatedClass_schema.json** `json schema <https://json-schema.org/understanding-json-schema/>`_ file of the evaluator or trading mode to configure.

It is also possible to manually edit each configuration file using a text editor for JSON. When configurable, each evaluator or trading mode has a **NameOfTheRelatedClass.json** file in the closest config folder.
