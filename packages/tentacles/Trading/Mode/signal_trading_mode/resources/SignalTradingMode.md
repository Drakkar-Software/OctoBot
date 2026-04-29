SignalTradingMode is a trading mode adapted to liquid and relatively flat markets. 
It will try to find reversals and trade them.  

This trading mode is using the daily trading mode orders system with adapted parameters.

Warning: SignalTradingMode only works on liquid markets because the [Klinger Oscillator](https://www.investopedia.com/terms/k/klingeroscillator.asp) 
from MoveSignalsStrategyEvaluator the requires enough volume and candles continuity to be accurate.