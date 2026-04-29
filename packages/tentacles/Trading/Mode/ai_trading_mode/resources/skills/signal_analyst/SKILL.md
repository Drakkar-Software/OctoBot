---
name: signal-analysis
description: Use this skill for analyzing market signals, price trends, volume patterns, and identifying potential trading opportunities from multiple data sources.
---

# signal-analysis

## Overview

This skill provides comprehensive guidance on analyzing market signals from price, volume, order flow, and news data to identify potential trading opportunities. Use this when processing raw market data to generate actionable signals.

## Instructions

### 1. Price Action Analysis

**Trend Identification**
- Uptrend: Series of higher highs and higher lows
- Downtrend: Series of lower highs and lower lows
- Ranging: Price oscillating between support and resistance

**Momentum Assessment**
- Strong momentum: Large candles with follow-through
- Weakening momentum: Smaller candles, wicks, indecision
- Divergence: Price vs momentum indicators disagreement

### 2. Volume Analysis

**Volume Patterns**
- Volume surge on breakout: Confirms strength
- Declining volume: Weakening trend
- Volume at support/resistance: Key decision points
- Unusual volume spikes: Investigate cause

**Order Flow Indicators**
- Buy/sell pressure imbalance
- Large orders vs small orders ratio
- Market vs limit order flow

### 3. Market Structure

**Key Levels**
- Support: Previous lows where buying emerged
- Resistance: Previous highs where selling emerged
- Breakout/breakdown levels
- Psychological round numbers

**Pattern Recognition**
- Consolidation before moves
- Failed breakouts (traps)
- Exhaustion gaps
- Climax patterns

### 4. Signal Quality Assessment

**High Quality Signals**
- Multiple timeframe confirmation
- Volume confirms price action
- Clear risk/reward setup
- Recent similar patterns worked

**Low Quality Signals**
- Conflicting timeframes
- Low volume, choppy price action
- Poor risk/reward
- High noise, low conviction

### 5. News and Events Impact

**High Impact Events**
- Major regulatory announcements
- Exchange listings/delistings
- Partnership announcements
- Security incidents

**Signal Integration**
- Positive news + bullish technicals = Strong buy signal
- Negative news + bearish technicals = Strong sell signal
- News conflicts with technicals = Wait for confirmation

## Output Format

```json
{
  "signals": [
    {
      "symbol": "BTC/USDT",
      "signal_type": "bullish" | "bearish" | "neutral",
      "strength": 0.8,
      "confidence": 0.75,
      "key_factors": [
        "Breakout above resistance with high volume",
        "Multiple timeframe alignment",
        "Positive news catalyst"
      ],
      "description": "Strong bullish breakout signal with volume confirmation",
      "entry_zone": {"min": 45000, "max": 46000},
      "targets": [48000, 50000, 52000],
      "stop_loss": 43500
    }
  ],
  "market_overview": "General market showing strength with Bitcoin leading, altcoins following"
}
```

## Best Practices

1. **Always consider timeframe context** - Align signals with higher timeframe trend
2. **Volume is critical** - Don't trust moves without volume
3. **Wait for confirmation** - Don't jump on weak signals
4. **Track signal performance** - Learn which patterns work best
5. **Be patient** - Quality over quantity
6. **Document patterns** - Save successful patterns to /memories/signals/
