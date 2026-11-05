Uses Nace's [Drex](https://console.nace.ai/docs/drex) decision model to predict the next move of the market.

Evaluates between -1 to 1 according to Drex's probability that the next candle closes up, the same way
GPTEvaluator uses ChatGPT's prediction and confidence. Other settings are GPTEvaluator's.

Requires the `NACE_API_KEY` environment variable. Without it, or when Drex can't be reached, ChatGPT is used
like in GPTEvaluator.

With `NACE_API_KEY`, this evaluator also works in backtesting on any market: Drex is asked for each candle.
