---
title: "Exchanges"
description: "Lean how to configure your exchange accounts for your OctoBot to trade using your exchange funds or simulated money."
sidebar_position: 7
---

# Exchanges


To know more about an exchange support in OctoBot, please have a look at [the exchange summary](/guides/exchanges).

## Web interface configuration


OctoBot reads trading data (prices, volumes, trades, etc) from exchanges. At least one exchange 
is required for OctoBot to perform trades. In [simulation mode](/guides/octobot-usage/simulator), 
exchange API keys configuration is not necessary.

![exchange accounts configuration in octobot](/images/guides/configuration/exchange-accounts-configuration-in-octobot.png)

You can configure OctoBot's exchanges using the [web interface](/guides/octobot-interfaces/web) 
**configuration** tab.

## Manual configuration


In **user/config.json**, find this lines:

``` json
"exchanges": {

}
```

Edit this lines and add the exchange(s) you want to use.

In OctoBot configuration, exchange connection info are encrypted. To manually add exchange configuration, you can add your info directly into your **user/config.json** file, OctoBot will then take care of the encryption for you.

If you want to encrypt your exchange keys before starting OctoBot, you
can use the following instructions:

Start the OctoBot with option **--encrypter** like below :

``` bash
python start.py --encrypter
```

And copy and paste your api-key and api-secret to your configuration file (see example below).

Example with Binance and Coinbase :

``` json
"exchanges": {
    "binance": {
        "api-key": "YOUR_BINANCE_API_KEY_ENCRYPTED",
        "api-secret": "YOUR_BINANCE_API_SECRET_ENCRYPTED",
        "sandboxed": false
    },
    "coinbasepro": {
        "api-key": "YOUR_EXCHANGE_API_KEY_ENCRYPTED",
        "api-secret": "YOUR_EXCHANGE_API_SECRET_ENCRYPTED",
        "api-password": "YOUR_EXCHANGE_API_SECRET_ENCRYPTED",
        "sandboxed": true
    }
}
```

-   **api-key** is your exchange account API key
-   **api-secret** is your exchange account API secret
-   **api-password** is your exchange account API password if this exchange is requiring a password. Leave empty otherwise
-   **sandboxed** if your exchange is supporting a sandbox(or testnet) mode, allows to trade on this version of the exchange

## Simulated exchange


To use the Simulated exchange feature of the OctoBot, you have to specify a [trader simulator](/guides/octobot-usage/simulator.md) configuration. To use an exchange in simulation only, you also have to specify its configuration as described above. For most exchanges, API credentials are not required in simulation mode, adding the exchange with default values is enough.
