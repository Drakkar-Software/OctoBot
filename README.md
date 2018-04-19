# CryptoBot [![Codacy Badge](https://api.codacy.com/project/badge/Grade/c83a127c42ba4a389ca86a92fba7c53c)](https://www.codacy.com/app/paul.bouquet/CryptoBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Trading-Bot/CryptoBot&amp;utm_campaign=Badge_Grade) [![Build Status](https://api.travis-ci.org/Trading-Bot/CryptoBot.svg?branch=dev)](https://travis-ci.org/Trading-Bot/CryptoBot)
#### Version 0.0.6-alpha
## Install
```
git clone https://github.com/Trading-Bot/CryptoBot
cd CryptoBot
sudo pip install -r requirements.txt
```

## Configuration
Create a **config.json** file in the **config folder** with the following example :
```
{
  "crypto_currencies": {
    "Bitcoin": {
      "pairs" : ["BTC/USDT"]
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
## Usage
```
python main.py
```
## Customize you CryptoBot !
### Adding implementations of any evaluator

To add another implementation of an existing evaluator, 3 simple steps:
1. Create a class **inheriting** the evaluator to improve
2. Store it in the evaluator's ```Advanced``` folder (in ```CryptoBot/evaluator/evaluator_type/Advanced```).
3. In this ```Advanced``` folder, create or update the ```__init__.py``` file to add the following line:
```python
from .file_containing_new_implementation_name.py import *
```
### Adding implementations of any analysis tool

To add another implementation of an existing analysis tool, 3 simple steps:
1. Create a class inheriting the analyser to improve
2. Store it in the ```Advanced``` folder (in ```CryptoBot/evaluator/Util/Advanced```).
3. In this ```Advanced``` folder, create or update the ```__init__.py``` file to add the following line:
```python
from .file_containing_new_implementation_name.py import *
```

More information and examples on the [wiki](https://github.com/Trading-Bot/CryptoBot/wiki/Customize-your-CryptoBot)

## Changelog
See [changelog file](https://github.com/Trading-Bot/CryptoBot/tree/master/docs/CHANGELOG.md)

## Demo
See live demo [here](https://twitter.com/HerklosBotCrypt)

## Testing
...

## More
For more details see the [project wiki](https://github.com/Herklos-Bots/CryptoBot/wiki).
