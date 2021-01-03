
Trader
======


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :alt: trading


Open your **user/config.json** file and edit this configuration :

.. code-block::

   "trader":{
     "enabled": true
   }

Enabled
^^^^^^^

The **Enabled** parameter is to be set at **true** when OctoBot should trade real cryptocurrencies. 
When **false** OctoBot will never any create a real trade. This **false** value can be used to make OctoBot only use its simulation mode on real market conditions.

Trading settings
================

.. code-block::

   "trading":{
     "multi-session-profitability": false,
     "reference-market": "BTC",
     "risk": 0.8
   }

Multi-session-profitability
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The **Multi-session-profitability** parameter defines whether or not OctoBot profritability should be reset at each start of the bot. If activated, as long as traded pairs configuration is not changing, the computed profitability will be computed taking the previous OctoBot executions into account. If the trader simulator is activated, it will also not reset its portfolio at each start but will continue from where it stopped in the previous execution. Default is false. 

Reference-market
^^^^^^^^^^^^^^^^

The **Reference-market** parameter defines which currency OctBot should use as a reference, this reference is used to compute profitability. 

Risk
^^^^

The **Risk** parameter defines the behaviour of OctoBot in an optimism manner.

It is a value between 0 and 1:


* A low risk (closer to 0) will make OctoBot a very safe trader with few bold moves and mostly small trades. A 0 risk bot is very pessimistic (regarding its orders creation) and does not expect big market moves.
* A high risk (closer to 1) will make OctoBot a very active and heavy trader. A 1 risk bot is very optimistic (regarding its orders creation) and is expecting significative market moves.

Trader simulator
----------------

Additionally to the real trading system, a trading simulator is available in OctoBot.

`Here is the article describing the simulator feature of OctoBot <https://github.com/Drakkar-Software/OctoBot/wiki/Simulator>`_
