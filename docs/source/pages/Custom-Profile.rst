
Custom Profile
================================

A custom profile allow to customize strategy and trading mode.

To create a custom profile :

- Open an existing profile page

- Click on duplicate button

.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_create_custom.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_create_custom.png
   :alt: trading_modes

Evaluator and trading configuration
-----------------------------------------------


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_strategies_select.png
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/profile_strategies_select.png
   :alt: trading_modes


**user/profiles/<profile_name>/tentacles_config.json** is a configuration file telling OctoBot which evaluators,
strategies and trading modes to use. It is kept up to date after each `Tentacle Manager <Tentacle-Manager.html>`_ usage (when new elements become available).

An example of **user/profiles/<profile_name>/tentacles_config.json** is available `as default_tentacles_config.json on github <https://github.com/Drakkar-Software/OctoBot/blob/master/octobot/config/default_tentacles_config.json>`_.

.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/evaluators.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/evaluators.jpg
   :alt: evaluators


Example of **tentacles_config.json**\ :

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

Please note that any evaluator or strategy that doesn't extend an element in **tentacles_config.json** has to be added to this file otherwise will be ignored by OctoBot.
When using the `Tentacle Manager <Tentacle-Manager.html>`_ to install tentacles, this is done automatically.
