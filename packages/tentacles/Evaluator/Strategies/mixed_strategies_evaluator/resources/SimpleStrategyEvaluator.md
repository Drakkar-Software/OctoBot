SimpleStrategyEvaluator is the most flexible strategy. Meant to be customized, it is using
every activated technical, social and real time evaluator, and averages the evaluation value of
each to compute its final evaluation.

This strategy can be used to make trading signals using as many evaluators as required.

Used time frames are 1h, 4h and 1d by default.

Warning: this strategy only considers evaluators with evaluations values between -1 and 1.
