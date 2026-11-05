CryptoLLMAIStrategyEvaluator answered by Nace's [Drex](https://console.nace.ai/docs/drex) decision model.

Drex reads the same evaluations as the LLM agents, along with what each evaluator type's eval note means (OctoBot's
technical and real-time evaluators use -1 for buy), and returns probabilities for five stances from strong sell to
strong buy. The eval note is the expected stance, from -1 (strong sell) to 1 (strong buy), like the LLM agents'
summary. One Drex request replaces the agent team's LLM calls.

Requires the `NACE_API_KEY` environment variable. Without it, or when Drex can't be reached, the LLM agents are used
like in CryptoLLMAIStrategyEvaluator.
