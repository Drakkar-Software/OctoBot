TechnicalAnalysisStrategyEvaluator a flexible technical analysis strategy. Meant to be customized, it is using 
every activated technical evaluator and averages the evaluation value of each to compute its final evaluation. 

This strategy makes it possible to assign a weight to any time frame in order to make the related technical evaluations 
more or less impactful for the final strategy evaluation. If not specified for a time frame, default weight is 50.

This strategy can be used to create custom trading signals using as many technical 
evaluators as desired.

TechnicalAnalysisStrategyEvaluator can also use real time evaluators to trigger an instant re-evaluation of its technical 
evaluators and react quickly. The evaluation value of these real time evaluators will not be considered in the final strategy 
evaluation as they are only meant to trigger an emergency re-evaluation.

Used time frames are 30m, 1h, 2h, 4h and 1d by default.

Warning: this strategy only considers evaluators with evaluations values between -1 and 1.
