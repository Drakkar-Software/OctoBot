# LLMAIStrategyEvaluator

The LLMAIStrategyEvaluator is an advanced strategy evaluator that leverages Large Language Models (LLMs) to analyze and synthesize signals from Technical Analysis (TA), Social sentiment, and Real-Time evaluators. It provides intelligent trading recommendations by combining multiple evaluator inputs with AI-driven reasoning through parallel sub-agent processing.

## How it works

1. **Signal Aggregation**: Collects evaluation notes and descriptions from configured TA, Social, and Real-Time evaluators
2. **Parallel Sub-Agent Analysis**: Uses specialized StrategyAgents to analyze each evaluator type independently
3. **AI Synthesis**: Leverages Large Language Model reasoning in each sub-agent for specialized analysis
4. **Summarization**: Combines all sub-agent results through a SummarizationAgent for final evaluation
5. **Output Generation**: Produces eval_note (-1 to 1) and descriptive reasoning

## File Structure

The LLMAIStrategyEvaluator is organized in a modular architecture:

```
ai_strategies_evaluator/
├── ai_strategies.py                 # Main evaluator implementation
├── agents/                          # Agent-based architecture
│   ├── __init__.py                  # Agent module exports
│   ├── base_llm_agent.py           # Abstract base agent class
│   ├── summarization_agent.py      # Final result synthesis
│   ├── technical_analysis_agent.py # TA signal analysis
│   ├── sentiment_analysis_agent.py # Social sentiment analysis
│   └── real_time_analysis_agent.py # Real-time market analysis
│   └── factory.py                  # Agent creation factory
├── config/                         # Configuration files
│   └── LLMAIStrategyEvaluator.json # Evaluator configuration
├── resources/                      # Documentation and metadata
│   ├── LLMAIStrategyEvaluator.md   # This documentation
│   └── metadata.json               # Tentacle metadata
├── tests/                          # Test suite
│   └── test_llm_ai_strategy_evaluator.py # Unit tests
└── __init__.py                     # Package initialization
```

### User Inputs
- **Prompt**: Custom prompt for LLM analysis (leave empty to use default specialized prompts per evaluator type)
- **Model**: GPT model selection (uses GPTService defaults if not specified)
- **Max Tokens**: Maximum response length (uses GPTService defaults if not specified)
- **Temperature**: Randomness in LLM responses (uses GPTService defaults if not specified)
- **Evaluator Types**: Select TA, Social, Real-Time evaluators to include (all enabled by default)
- **Output Format**: Choose "standard" or "with_confidence" (includes average confidence level)

### Default Behavior
- Evaluates on 1-hour, 4-hour, and 1-day timeframes
- Uses GPTService default model and parameters
- Includes TA, Social, and Real-Time evaluators by default
- Provides specialized analysis for each evaluator type
- Uses parallel processing for improved performance

### Specialized Analysis Types

#### Technical Analysis Agent
Focuses exclusively on technical indicators and price patterns:
- Analyzes RSI, MACD, moving averages, Bollinger Bands, ADX, etc.
- Assesses trend direction and indicator convergence
- Provides confidence based on signal strength and agreement

#### Social Sentiment Agent
Focuses exclusively on social and sentiment signals:
- Analyzes social media, news, community discussions
- Assesses overall market mood and sentiment
- Provides confidence based on signal consistency and volume

#### Real-Time Agent
Focuses on live market movements and instant fluctuations:
- Analyzes order book data and real-time price movements
- Assesses current buying/selling pressure
- Provides confidence based on signal volatility and recency

## Requirements
- GPTService must be configured and activated
- At least one TA, Social, or Real-Time evaluator should be active for meaningful analysis
- Works in both live and backtesting modes

## Use Cases
- Advanced signal synthesis from multiple evaluator types
- Parallel AI-powered market analysis for improved performance
- Specialized analysis combining technical, social, and real-time signals
- Automated trading decisions with multi-faceted AI reasoning
- Backtesting complex multi-signal strategies

## Architecture Benefits

### Parallel Processing
- Each evaluator type is analyzed by a dedicated agent running in parallel
- Improved performance and reduced latency compared to sequential processing
- Better resource utilization of LLM API calls

### Specialized Analysis
- Each sub-agent focuses on its domain expertise
- More accurate analysis through domain-specific prompts and reasoning
- Consistent evaluation methodology across different signal types

### Intelligent Summarization
- Final evaluation considers all sub-agent results
- Weights signals based on confidence and consistency
- Provides comprehensive reasoning across all analysis domains

## Warning
- LLM responses may vary due to temperature settings
- Requires OpenAI API access through GPTService
- Parallel processing increases API usage and costs
- Performance depends on quality of input evaluator signals