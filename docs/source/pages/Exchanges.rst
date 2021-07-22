
Exchanges
=========

Web interface configuration
---------------------------

Octobot reads trading data (prices, volumes, trades, etc) from exchanges. At least one exchange is required for OctoBot to perform trades. In `simulation mode <Simulator.html#simulator>`_\ , exchange API keys configuration is not necessary.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/exchanges.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/exchanges.jpg
   :alt: exchanges

You can configure OctoBot's exchanges using the `web interface <Web-interface.html>`_ **configuration** tab.

Manual configuration
--------------------

In **user/config.json**\ , find this lines:

.. code-block:: json

   "exchanges": {

   }

Edit this lines and add the exchange(s) you want to use. 

In OctoBot configuration, exchange connection info are encrypted.
To manually add exchange configuration, you can add your info directly into your **user/config.json** file, OctoBot will then take care of the encryption for you.

If you want to encrypt your exchange keys before starting OctoBot, you can use the following instructions:

Start the OctoBot with option **--encrypter** like below :

.. code-block:: bash

   python start.py --encrypter

And copy and paste your api-key and api-secret to your configuration file (see example below).

Example with Binance and Coinbase Pro :

.. code-block:: json

   "exchanges": {
       "binance": {
           "api-key": "YOUR_BINANCE_API_KEY_ENCRYPTED",
           "api-secret": "YOUR_BINANCE_API_SECRET_ENCRYPTED"
       },
       "coinbasepro": {
           "api-key": "YOUR_EXCHANGE_API_KEY_ENCRYPTED",
           "api-secret": "YOUR_EXCHANGE_API_SECRET_ENCRYPTED",
           "api-password": "YOUR_EXCHANGE_API_SECRET_ENCRYPTED"
       }
   }


* **api-key** is your exchange account API key
* **api-secret** is your exchange account API secret
* **api-password** is your exchange account API password if this exchange is requiring a password. Leave empty otherwise

Partner exchanges - Support OctoBot
-----------------------------------

As the OctoBot team, **our goal is to keep providing OctoBot for free**.
However developing and maintaining the project comes at a cost. Therefore we rely
on exchanges partnerships to propose the most convenient way to support OctoBot.

By using OctoBot on real trading with our partner exchanges, you contribute to
support the project and it won't cost you any money.

If an account you are using is not meeting a partner exchange requirement, you will
see an error message: this doesn't prevent your from using OctoBot.
However the OctoBot team would greatly appreciate if you could create a
new account that meets the exchange's requirements to support the project.

Here are the current partners:

Binance
^^^^^^^
Binance has 2 accounts requirements to support OctoBot:

* A relatively new account (after july 1st 2021)
* No referral code on the account

In case your current account is not meeting these criteria, you can
support OctoBot by creating a new account (without adding any referral id)
on https://www.binance.com/.

Please note that thanks to `Internal Transfers <https://www.binance.com/en-NG/support/faq/360037037312>`_,
you can move your funds quickly and for free between Binance accounts.

OctoBot officially supported exchanges
--------------------------------------

.. list-table::
   :header-rows: 1

   * - Exchange
     - SPOT (REST)
     - Websocket
     - Margin & Future
     - Simulated
     - Community tested
   * - Binance
     - 100%
     - 80%
     - 0%
     - 100%
     - yes
   * - Kucoin
     - 100%
     - 0%
     - 0%
     - 100%
     - yes
   * - Coinbase Pro
     - 100%
     - 0%
     - 0%
     - 100%
     - yes
   * - BitMax
     - 100%
     - 0%
     - 0%
     - 100%
     - -
   * - Bybit
     - 80%
     - 0%
     - 0%
     - 100%
     - -
   * - Kraken
     - 75% (only supplies the total balance)
     - 0%
     - 0%
     - 100%
     - yes
   * - Bitfinex
     - 75%
     - 0%
     - 0%
     - 100%
     - -
   * - Bittrex
     - 75%
     - 0%
     - 0%
     - 100%
     - -
   * - Bitmex
     - 75%
     - 30%
     - 0%
     - 90%
     - -
   * - COSS
     - 75%
     - 0%
     - 0%
     - 100%
     - yes
   * - Bitstamp
     - 10%
     - 0%
     - 0%
     - 100%
     - -
   * - OKEX
     - 10%
     - 0%
     - 0%
     - 100%
     - -
   * - Poloniex
     - 0%
     - 0%
     - 0%
     - 100%
     - -
   * - Cryptopia
     - 0%
     - 0%
     - 0%
     - 100%
     - -


**Supported techologies** : 

*REST* : **slow** and **limited** requests

*Websocket* : **high speed** and **no limit**

If you want use any exchange that is available `here <https://github.com/ccxt/ccxt/wiki/Exchange-Markets>`_\ , the REST interface should work but **it's at your own risk** since we did not test it yet.

For simulated only exchanges, see the "Simulated exchange" section below.

Simulated exchange
------------------

To use the Simulated exchange feature of the Octobot, you have to specifiy a `\ trader simulator <Simulator.html>`_ configuration.
To use an exchange in simulation only, you also have to specify its configuration as described above. For most exchanges,  API credentials are not required in simulation mode, adding the exchange with default values is enough. 
