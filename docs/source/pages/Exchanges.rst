
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
           "api-secret": "YOUR_BINANCE_API_SECRET_ENCRYPTED",
           "web-socket": true
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
* **web-socket** is a setting telling OctoBot whether or not to try to use websockets interfaces (websockets are used to get close to real-time data update but it's using more bandwidth). Moreover, RealTime evaluators are much better with websockets enabled.

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
