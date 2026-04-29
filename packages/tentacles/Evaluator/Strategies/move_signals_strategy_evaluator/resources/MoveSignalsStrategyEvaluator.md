MoveSignalsStrategyEvaluator is a fractal strategy: it is using different time frames to
balance decisions. 

This strategy is using the KlingerOscillatorMomentumEvaluator based on the [Klinger Oscillator](https://www.investopedia.com/terms/k/klingeroscillator.asp)
to know when to start a trade and BBMomentumEvaluator based on [Bollinger Bands](https://www.investopedia.com/terms/b/bollingerbands.asp)
to know how much weight to give to this trade. 

This strategy is updated at the end of each candle on the watched time frame which is each 30 minutes. 

It is also possible to make it trigger 
automatically using a real-time evaluator. Using a real time evaluator that signals sudden market changes like the 
InstantFluctuationsEvaluator will make MoveSignalsStrategyEvaluator also wake up on such events.

Used time frames are 30m, 1h and 4h. 

Warning: MoveSignalsStrategyEvaluator only works on liquid markets because the Klinger Oscillator requires enough 
volume and candles continuity to be accurate.