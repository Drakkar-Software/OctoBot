# CryptoBot [![Codacy Badge](https://api.codacy.com/project/badge/Grade/c83a127c42ba4a389ca86a92fba7c53c)](https://www.codacy.com/app/paul.bouquet/CryptoBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Trading-Bot/CryptoBot&amp;utm_campaign=Badge_Grade) [![Build Status](https://api.travis-ci.org/Trading-Bot/CryptoBot.svg?branch=dev)](https://travis-ci.org/Trading-Bot/CryptoBot)
#### Version 0.0.5-alpha
## Install
```
git clone https://github.com/Trading-Bot/CryptoBot
cd CryptoBot
sudo pip install git+https://github.com/Herklos-Bots/BotCore
sudo pip install -r requirements.txt
```

## Configuration
Create a **config.json** file in the **config folder** with the following example :
```
{
  "crypto_currencies": {
    "Bitcoin": {
      "pairs" : ["BTC/USDT"],
      "twitters" : ["GuillaGjum","RedditBTC","BTCFoundation"]
    }
  },
  "exchanges": {
    "binance": {
      "api-key": "YOUR_BINANCE_API_KEY",
      "api-secret": "YOUR_BINANCE_API_SECRET"
    }
  },
  "notification":{
    "enabled": true,
    "type": [1, 2]
  },
  "trader":{
    "enabled": false,
    "risk": 1
  },
  "simulator":{
    "enabled": true,
    "risk": 1,
    "starting_portfolio": {
      "BTC": 10,
      "USDT": 1000
    }
  },
  "services": {
    "mail": {
      "gmail_user": "YOUR_GMAIL_USERNAME",
      "gmail_password": "YOUR_GMAIL_PASSWORD",
      "mail_dest": "YOUR_DESTINATION_MAIL"
    },
    "twitter": {
      "api-key": "YOUR_TWITTER_API_KEY",
      "api-secret": "YOUR_TWITTER_API_SECRET",
      "access-token": "YOUR_TWITTER_ACCESS_TOKEN",
      "access-token-secret": "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
    }
  },
  }
}
```
## Changelog

For more details see the [project wiki](https://github.com/Herklos-Bots/CryptoBot/wiki).
