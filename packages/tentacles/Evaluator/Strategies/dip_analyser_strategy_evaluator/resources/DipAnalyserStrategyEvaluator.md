DipAnalyserStrategyEvaluator is a strategy analysing market dips using [RSI](https://www.investopedia.com/terms/r/rsi.asp) 
averages. According to the level of the RSI, a buy signal can be generated. This signal has a weight that corresponds to 
a higher or lower intensity of the RSI evaluation.
 
This strategy also uses the [Klinger oscillator](https://www.investopedia.com/terms/k/klingeroscillator.asp) to identify 
reversals and create buy signals. 

A buy signal is generated when the RSI component is signaling an opportunity and the Klinger part is confirming 
a reversal situation.

This strategy is updated at the end of each candle on the watched time frame. 

It is also possible to make it trigger 
automatically using a real-time evaluator. Using a real time evaluator that signals sudden market changes like the 
InstantFluctuationsEvaluator will make DipAnalyserStrategyEvaluator also wake up on such events.

DipAnalyserStrategyEvaluator focuses on one time frame only and works best on larger time frames such as 4h and more.