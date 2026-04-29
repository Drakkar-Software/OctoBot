DeathAndGoldenCrossEvaluator is based on two [moving averages](https://www.investopedia.com/terms/m/movingaverage.asp), by default one of **50** periods and other one of **200**.

If the fast moving average is above the slow moving average, this indicates a bull market (signal: -1) When this happens it's called a [Golden Cross](https://www.investopedia.com/terms/g/goldencross.asp).
Inversely, if it's the fast moving average which is above the slow moving average this indicates a bear market (signal: 1). When this happens it's called a [Death Cross](https://www.investopedia.com/terms/d/deathcross.asp)

This evaluator will always produce a value of `0` except right after a golden or death cross 
is found, in this case a `-1` or `1` value will be produced.
