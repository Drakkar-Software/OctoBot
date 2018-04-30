# CryptoBot [![Codacy Badge](https://api.codacy.com/project/badge/Grade/c83a127c42ba4a389ca86a92fba7c53c)](https://www.codacy.com/app/paul.bouquet/CryptoBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Trading-Bot/CryptoBot&amp;utm_campaign=Badge_Grade) [![Build Status](https://api.travis-ci.org/Trading-Bot/CryptoBot.svg?branch=dev)](https://travis-ci.org/Trading-Bot/CryptoBot)

#### Version 0.0.9-alpha ([changelog](https://github.com/Trading-Bot/CryptoBot/tree/alpha/docs/CHANGELOG.md))

## Disclaimer
This software is for educational purposes only. Do not risk money which 
you are afraid to lose. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS 
AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. 

Always start by running a trading bot in simulation mode and do not engage money
before you understand how it works and what profit/loss you should
expect.

We strongly recommend you to have coding and Python knowledge. Do not 
hesitate to read the source code and understand the mechanism of this bot.

Moreover, we are in the **alpha** phase so you should not expect the bot to be stable.

## Demo
See live demo [here](https://twitter.com/HerklosBotCrypt)

## Install
See [installation wiki page](https://github.com/Trading-Bot/CryptoBot/wiki/Installation)
<br>With python3 : 
```
git clone https://github.com/Trading-Bot/CryptoBot
cd CryptoBot
pip install -r requirements.txt
```

## Configuration
Create a **config.json** file in the **config folder** with the following example :
```
Rename config/default_config.json to config/config.json
```

### More configuration
See [Configuration Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Configuration)
```json
"crypto_currencies": {
    "Bitcoin": {
      "pairs" : ["BTC/USDT"]
    }
}
```
See [Exchanges Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Exchanges)
```json
"exchanges": {
    "binance": {
      "api-key": "",
      "api-secret": ""
    }
}
```
See [Notifications Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Notifications)
```json
"notification":{
    "enabled": true,
    "type": [1, 2]
}
```
See [Trader Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Trader)
```json
"trader":{
    "enabled": false,
    "risk": 0.5
}
```
See [Simulator Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Simulator)
```json
"simulator":{
    "enabled": true,
    "risk": 0.5,
    "starting_portfolio": {
      "BTC": 10,
      "USDT": 1000
    }
}
```
See [Services Wiki](https://github.com/Herklos-Bots/CryptoBot/wiki/Services)
```json
"services": {}
```
  
## Usage
```bash
python start.py
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

## Testing
Use *pytest* command in the root folder : 
```bash
pytest
```

## Changelog
See [changelog file](https://github.com/Trading-Bot/CryptoBot/tree/master/docs/CHANGELOG.md)

## More
For more details see the [project wiki](https://github.com/Herklos-Bots/CryptoBot/wiki).
