# Where are evaluators and strategies ?

Because OctoBot is modular, a wide range of evaluators and strategies are usable.

Default evaluators and strategies are located here: [https://github.com/Drakkar-Software/OctoBot-Packages](https://github.com/Drakkar-Software/OctoBot-Packages).

To install default evaluators and strategies in your OctoBot, run the following command: 

```bash
python start.py -p install all
```


It is also possible to specify which module(s) to install by naming it(them). In this case only the modules available in the available packages can be installed.
```
python start.py -p install forum_evaluator john_smith_macd_evaluator advanced_twitter_evaluator
```

**You can find how to create your OctoBot evaluators and strategies [here](https://github.com/Drakkar-Software/OctoBot/wiki/Customize-your-OctoBot).**
