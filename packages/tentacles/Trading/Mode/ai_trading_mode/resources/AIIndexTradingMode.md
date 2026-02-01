# AI Index Trading Mode

## Overview

The **AI Index Trading Mode** is an advanced trading mode that inherits from `IndexTradingMode` and uses external AI agents to dynamically generate portfolio distributions based on strategy evaluation data. This mode combines the robust rebalancing infrastructure of index trading with AI-driven decision making for optimal asset allocation, where AI logic is handled by separate agents rather than embedded in the mode.

## Key Features

- **Agent-Driven Allocations**: Uses external AI agents to analyze strategy signals and generate optimal portfolio weights
- **Strategy Integration**: Collects data from TA, Social, and Real-time evaluator signals on matrix callbacks
- **Decoupled AI**: AI processing happens in separate agents, allowing for scalability and modularity
- **Detailed Instructions**: Agents provide actionable rebalance instructions with explanations
- **Inherits IndexTradingMode**: Full rebalancing, order management, and portfolio optimization capabilities
- **Configurable Parameters**: Model selection, temperature, token limits for agents

## Configuration

### AI Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | "gpt-4" | GPT model used by agents (gpt-3.5-turbo, gpt-4, gpt-4-turbo) |
| `temperature` | float | 0.3 | AI creativity for agents (0.0 = deterministic, 1.0 = very creative) |
| `max_tokens` | int | 2000 | Maximum tokens for agent AI responses |

### Index Trading Parameters (inherited)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `refresh_interval` | int | 1 | Days between rebalance checks |
| `rebalance_trigger_min_percent` | int | 5 | Minimum % deviation before rebalance |

## How It Works

### 1. Strategy Signal Collection
The AI Index Trading Mode monitors matrix callbacks from strategy evaluators:
- Technical Analysis (TA) signals
- Social sentiment signals
- Real-time evaluation signals

### 2. Data Submission
When strategies update, the mode:
1. Collects current strategy evaluation data
2. Submits neutral evaluations with `{"strategy_data": data}` to trigger agent processing
3. Agents listen for these submissions and process the data

### 3. Agent Processing
External AI agents:
1. Receive strategy data from mode submissions
2. Analyze signals using configured GPT models
3. Generate rebalance instructions
4. Provide instructions back to the mode

### 4. Instruction Application
The mode receives agent-generated instructions:
- Applies distribution changes via `ai_index_distribution.apply_ai_instructions`
- Validates instructions for consistency
- Executes rebalancing using IndexTradingMode logic

## Agent Architecture

### Data Flow
```
Strategy Callbacks → Mode Producer → Submit {"strategy_data": data}
                        ↓
                Agents Process → Generate {"ai_instructions": instructions}
                        ↓
Mode Consumer → Apply Instructions → Rebalance Portfolio
```

### Instruction Format
Agents provide instructions as lists of actions:
```json
[
  {"action": "reduce_exposure", "symbol": "BTC", "amount": 10, "explanation": "Overbought signals"},
  {"action": "increase_exposure", "symbol": "ETH", "amount": 15, "explanation": "Strong momentum"}
]
```

### Agent Responsibilities
- **Signal Analysis**: Process strategy data with AI models
- **Instruction Generation**: Create validated rebalance actions
- **Error Handling**: Handle API failures and provide safe instructions

## Usage Examples

### Basic Configuration
```json
{
  "trading_mode": "AIIndexTradingMode",
  "model": "gpt-4",
  "temperature": 0.3,
  "max_tokens": 2000,
  "refresh_interval": 1,
  "rebalance_trigger_min_percent": 5
}
```

### Conservative Configuration
```json
{
  "trading_mode": "AIIndexTradingMode",
  "model": "gpt-3.5-turbo",
  "temperature": 0.1,
  "max_tokens": 1500,
  "refresh_interval": 2
}
```

## Testing

Use the tentacles-agent tools to test:
```bash
# Test with strategy evaluators
python tentacle_trading_mode_tester.py --mode AIIndexTradingMode --evaluators strategy_evaluators.json --symbol BTC/USDT --duration 120

# Test basic functionality
python tentacle_configuration_tester.py --config ai_index_config.json --validate
```

## Dependencies

- **AI Agents**: Required for instruction generation
- **Strategy Evaluators**: Any evaluators providing TA/Social/Real-time signals
- **IndexTradingMode**: Inherited rebalancing functionality

## Troubleshooting

### Common Issues

**No rebalancing occurs**
- Verify strategy evaluators are active and triggering callbacks
- Check that agents are running and processing submissions
- Ensure sufficient portfolio balance for rebalancing

**Agents not responding**
- Check agent configuration and connectivity
- Verify AI service availability
- Review agent logs for processing errors

### Logs to Check
- Strategy data submissions: `"Submitting strategy data for AI processing"`
- Instruction application: `"Applied AI instructions: {...}"`
- Validation errors: `"Invalid AI instructions received"`

## Future Enhancements

- **Agent Marketplace**: Multiple competing AI agents
- **Historical Learning**: Agents incorporate backtesting results
- **Real-time Adaptation**: Agents adjust to live market conditions
- **Multi-Asset Correlation**: Advanced portfolio optimization
- **Custom Agent Development**: Framework for user-defined agents