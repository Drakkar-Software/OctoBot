# CryptoBot - Alpha version
## Install
```
git clone https://github.com/Herklos-Bots/CryptoBot
cd CryptoBot
sudo pip install git+https://github.com/Herklos-Bots/BotCore
sudo pip install -r requirements.txt
```

## Configuration
Create a **config.json** file in the **config folder** with the following example :
```
{
  "exchanges": {
    "binance": {
      "api-key": "YOUR_BINANCE_API_KEY",
      "api-secret": "YOUR_BINANCE_API_SECRET"
    }
  },
  "notification":{
    "enabled": true,
    "type": 1,
    "mail_dest": "your_destination_mail@xxx.com"
  },
  "trader":{
    "enabled": false,
    "risk": 1
  }
}
```
## Changelog

For more details see the [project wiki](https://github.com/Herklos-Bots/CryptoBot/wiki).
