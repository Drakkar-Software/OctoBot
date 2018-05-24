# Default evaluators are located in [https://github.com/Trading-Bot/CryptoBot-Package-Template](https://github.com/Trading-Bot/CryptoBot-Package).

To install them in your CryptoBot, run the command 

```bash
python start.py -p install all
```


It is also possible to specify which module(s) to install by naming it(them). In this case only the modules available in the available packages can be installed.
```
python start.py -p install forum_evaluator john_smith_macd_evaluator advanced_twitter_evaluator
```
