---
name: technical-analysis
description: Use this skill for analyzing technical indicators like RSI, MACD, Moving Averages, Bollinger Bands, and price action patterns to assess market trends and momentum.
---

# technical-analysis

## Overview

This skill provides comprehensive guidance on analyzing technical indicators to evaluate market conditions and generate trading signals. Use this for any technical analysis-related questions or when you need to interpret indicator values.

## Instructions

### 1. Understand Key Technical Indicators

**RSI (Relative Strength Index)**
- Range: 0-100
- Oversold: < 30 (potential buy signal)
- Overbought: > 70 (potential sell signal)
- Divergence: Price makes new high/low but RSI doesn't (reversal signal)

**MACD (Moving Average Convergence Divergence)**
- Components: MACD line, Signal line, Histogram
- Bullish crossover: MACD crosses above signal line
- Bearish crossover: MACD crosses below signal line
- Histogram: Shows momentum strength

**Moving Averages**
- Short-term (SMA/EMA 20): Recent trend
- Medium-term (SMA/EMA 50): Intermediate trend
- Long-term (SMA/EMA 200): Major trend
- Golden cross: 50 MA crosses above 200 MA (bullish)
- Death cross: 50 MA crosses below 200 MA (bearish)

**Bollinger Bands**
- Upper/Lower bands: Volatility boundaries
- Price near upper band: Potentially overbought
- Price near lower band: Potentially oversold
- Band squeeze: Low volatility (potential breakout coming)
- Band expansion: High volatility (trend in motion)

### 2. Analyze Multiple Timeframes

When analyzing indicators, consider multiple timeframes:
- **1H/4H**: Short-term trading signals
- **1D**: Medium-term trend confirmation
- **1W**: Long-term trend direction

Higher timeframes carry more weight for trend direction.

### 3. Look for Indicator Convergence

Strong signals occur when multiple indicators agree:
- RSI oversold + MACD bullish crossover + price above 50 MA = Strong buy
- RSI overbought + MACD bearish crossover + price below 50 MA = Strong sell

### 4. Assess Trend Strength

Determine if the market is:
- **Strong uptrend**: Price above all MAs, RSI 50-70, MACD positive and rising
- **Strong downtrend**: Price below all MAs, RSI 30-50, MACD negative and falling
- **Ranging/Consolidation**: Price oscillating around MAs, RSI 40-60, MACD near zero

### 5. Identify Support and Resistance

- Previous highs/lows
- Moving averages acting as dynamic support/resistance
- Bollinger Bands as volatility-based support/resistance
- Round numbers (psychological levels)

### 6. Volume Analysis

- Rising volume on breakouts confirms strength
- Declining volume on rallies suggests weakness
- Volume spikes often precede reversals

## Output Format

When analyzing technical indicators, provide:
```json
{
  "eval_note": <float -1 to 1>,
  "confidence": <float 0-1>,
  "trend": "uptrend" | "downtrend" | "ranging",
  "key_indicators": ["RSI oversold at 28", "MACD bullish crossover", "Price above 50 MA"],
  "description": "Detailed analysis explaining the reasoning"
}
```

## Common Patterns

**Bullish Reversal Signs**
- RSI divergence (price lower low, RSI higher low)
- MACD histogram turning positive
- Price bouncing off support
- Volume spike on upward move

**Bearish Reversal Signs**
- RSI divergence (price higher high, RSI lower high)
- MACD histogram turning negative
- Price rejected at resistance
- Volume spike on downward move

## Best Practices

1. Never rely on a single indicator - use multiple confirmations
2. Consider the broader market context and trend
3. Account for timeframe - align trade direction with higher timeframe trend
4. Adjust interpretation for different market conditions (trending vs ranging)
5. Be aware of false signals in choppy, low-volume markets
