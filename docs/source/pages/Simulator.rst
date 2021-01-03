
Simulator
=========

OctoBot can be used in a simulation mode. In this mode, whether there is a real trading mode enabled or not, OctoBot will simulate trades using the exact same data as with the real trading mode. Real traders and trader_simulators are idependant.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/trading.jpg
   :alt: trading


The only difference with a real trader is in the available portfolio that is to be set in the **user/config.json** file. This portfolio will be managed by OctoBot and simulated orders will be using these available cryptocurrencies as a basis. The trader simulator will use the exchanges' last trades to figure out if the current orders would have been filled or not. If they would have been filled, the current simulated portfolio is updated accordingly

Setup the trader_simulator
--------------------------

Create in **user/config.json** the trader_simulator key :

.. code-block:: json

   "trader-simulator":{
     "enabled": true,
     "fees": {
         "maker": 0.07,
         "taker": 0.07
     },
     "starting-portfolio": {
       "BTC": 10,
       "USDT": 1000
     }
   }

Enabled
^^^^^^^

Set **enabled** to true to start a trader simulator when starting OctoBot. A trader simulator can be running with a real trader in a single OctoBot, the only difference between them will be the amount of available cryptocurrencies.

Fees
^^^^

Fees in % to be deducted at simulated orders completion in backtesting.

Starting portfolio
^^^^^^^^^^^^^^^^^^

This is the imaginary portfolio given to the trader simulator to create its orders with. It can contain any amount of any cryptocurrency. If these cryptocurrencies are in the **crypto-currencies** configuration, they will be traded as if they were from a real portfolio.

The starting portfolio is also **used for backtesting**.

This portfolio is reset at each start of the bot unless `Multi-session-profitability <https://github.com/Drakkar-Software/OctoBot/wiki/Trader#multi-session-profitability>`_ parameter is activated.

Mode, Reference-market and Risk
-------------------------------

These parameters are defined in the **trading** section, which is used by the trader simulator as well as the real trader. This **trading** section is described on the `real trader page <https://github.com/Drakkar-Software/OctoBot/wiki/Trader#trading-settings>`_

Real trader
-----------

Additionally to the simulated trading system, a real trader is available in OctoBot.

`Here is the article describing the real trader feature of OctoBot <https://github.com/Drakkar-Software/OctoBot/wiki/Trader>`_
