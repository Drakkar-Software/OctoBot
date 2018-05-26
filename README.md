# CryptoBot [![Codacy Badge](https://api.codacy.com/project/badge/Grade/c83a127c42ba4a389ca86a92fba7c53c)](https://www.codacy.com/app/paul.bouquet/CryptoBot?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Trading-Bot/CryptoBot&amp;utm_campaign=Badge_Grade) [![Build Status](https://api.travis-ci.org/Trading-Bot/CryptoBot.svg?branch=dev)](https://travis-ci.org/Trading-Bot/CryptoBot) [![Coverage Status](https://coveralls.io/repos/github/Trading-Bot/CryptoBot/badge.svg?branch=dev)](https://coveralls.io/github/Trading-Bot/CryptoBot?branch=dev)

#### Version 0.0.11-alpha ([changelog](https://github.com/Trading-Bot/CryptoBot/tree/alpha/docs/CHANGELOG.md))

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
**See [installation wiki page](https://github.com/Trading-Bot/CryptoBot/wiki/Installation)**

## Configuration
Create a **config.json** file in the **config folder** with the following example :
```
Rename config/default_config.json to config/config.json
```

## Usage
### Start the bot
```bash
python start.py
```
### Start the bot in simulation mode
```bash
python start.py --simulate
```
### Start the bot in backtesting mode
```bash
python start.py --backtesting
```
### Start the bot with interfaces (web / telegram)
```bash
python start.py --web 
python start.py --telegram
python start.py --web --telegram 
```
### Start the bot in data collector mode (for backtesting)
```bash
python start.py --data_collector
```
## Customize you CryptoBot !
Information and examples on the [wiki](https://github.com/Trading-Bot/CryptoBot/wiki/Customize-your-CryptoBot)

## Screenshots
TODO

## Testing
Use *pytest* command in the root folder : 
```bash
pytest
```

## Changelog
See [changelog file](https://github.com/Trading-Bot/CryptoBot/tree/master/docs/CHANGELOG.md)

## More
For more details see the [project wiki](https://github.com/Herklos-Bots/CryptoBot/wiki).
