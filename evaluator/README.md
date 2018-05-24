# Where are evaluators and strategies ?
Because CryptoBot is modular, a wide range of evaluators and strategies are usable.

Default evaluators and strategies are located here: [https://github.com/Trading-Bot/CryptoBot-Packages](https://github.com/Trading-Bot/CryptoBot-Packages).

To install default evaluators and strategies in your CryptoBot, run the command 

```bash
python start.py -p install all
```


It is also possible to specify which module(s) to install by naming it(them). In this case only the modules available in the available packages can be installed.
```
python start.py -p install forum_evaluator john_smith_macd_evaluator advanced_twitter_evaluator
```

**You can find how to create your CryptoBot evaluators and strategies [here](https://github.com/Trading-Bot/CryptoBot/wiki/Customize-your-CryptoBot).**
