# Where are evaluators and strategies ?
Because Octobot is modular, a wide range of evaluators and strategies are usable.

Default evaluators and strategies are located here: [https://github.com/Drakkar-Software/Octobot-Packages](https://github.com/Drakkar-Software/Octobot-Packages).

To install default evaluators and strategies in your Octobot, run the command 

```bash
python start.py -p install all
```


It is also possible to specify which module(s) to install by naming it(them). In this case only the modules available in the available packages can be installed.
```
python start.py -p install forum_evaluator john_smith_macd_evaluator advanced_twitter_evaluator
```

**You can find how to create your Octobot evaluators and strategies [here](https://github.com/Drakkar-Software/Octobot/wiki/Customize-your-Octobot).**
