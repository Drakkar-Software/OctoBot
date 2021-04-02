
Trader
======


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :alt: trading


Open your **user/profiles/<profile_name>/profile.json** file and edit this configuration :

.. code-block:: json

   "trader":{
     "enabled": true,
     "load-trade-history": false
   }

Enabled
^^^^^^^

When the **Enabled** parameter is set at **true**, OctoBot will trade using your real funds from your exchange's accounts.
When **false** OctoBot will never any create a real trade.

Load trade history
^^^^^^^^^^^^^^^^^^

When the **load-trade-history** parameter is set at **true**, OctoBot will load the account's recent trades for
the enabled traded pairs at startup. This allows to have a view on your account's trade history.
When **false**, OctoBot will only historize trades that happen after the bot startup.

Trading settings
-----------------

.. code-block:: json

   "trading":{
     "reference-market": "BTC",
     "risk": 0.8
   }

Reference-market
^^^^^^^^^^^^^^^^

The **Reference-market** parameter defines which currency OctBot should use as a reference,
this reference is used to compute profitability and the portfolio total value

Risk
^^^^

The **Risk** parameter defines the behaviour of OctoBot in an optimism manner.

It is a value between 0 and 1:


* A low risk (closer to 0) will make OctoBot a very safe trader with few bold moves and mostly small trades. A 0 risk bot is very pessimistic (regarding its orders creation) and does not expect big market moves.
* A high risk (closer to 1) will make OctoBot a very active and heavy trader. A 1 risk bot is very optimistic (regarding its orders creation) and is expecting significative market moves.

Trader simulator
----------------

Additionally to the real trading system, a trading simulator is available in OctoBot.

`Here is the article describing the simulator feature of OctoBot <Simulator.html>`_
