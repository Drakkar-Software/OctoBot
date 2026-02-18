---
name: trading-strategy
description: Use this skill for developing and evaluating trading strategies by synthesizing technical analysis, market sentiment, and risk management principles into actionable trading recommendations.
---

# trading-strategy

## Overview

This skill provides comprehensive guidance on synthesizing multiple analyses into coherent trading strategies and actionable recommendations. Use this for final decision-making and trade structuring.

## Instructions

### 1. Synthesize Multiple Signals

Integrate analysis from different sources:
- **Technical Analysis**: Trend, momentum, support/resistance
- **Sentiment Analysis**: Market mood, fear/greed levels
- **Real-Time Data**: Order flow, liquidity, recent price action

Weight each component by:
- Confidence level (higher confidence = higher weight)
- Timeframe alignment (multiple timeframes agreeing)
- Signal strength (strong vs weak signals)

### 2. Resolve Conflicting Signals

When analyses disagree:
- **Technical bullish, Sentiment bearish**: Often means "buy the dip" if technical is strong
- **Technical bearish, Sentiment bullish**: Often means "sell the rally" if technical is strong
- **Mixed timeframes**: Defer to higher timeframe for trend direction
- **Low confidence all around**: Recommend staying out or reducing position size

### 3. Generate eval_note (-1 to 1 scale)

**Strong Buy Signals (0.6 to 1.0)**
- Multiple timeframes aligned bullish
- Technical indicators show strong uptrend
- Sentiment at extreme fear (contrarian buy)
- High confidence from all analyses

**Moderate Buy (0.3 to 0.6)**
- Majority of signals bullish
- Some conflicting indicators
- Medium confidence
- Trend supports upside

**Neutral (−0.3 to 0.3)**
- Mixed signals across analyses
- Ranging market conditions
- Low confidence or uncertainty
- Wait for clearer setup

**Moderate Sell (−0.6 to −0.3)**
- Majority of signals bearish
- Some conflicting indicators  
- Medium confidence
- Trend supports downside

**Strong Sell (−1.0 to −0.6)**
- Multiple timeframes aligned bearish
- Technical indicators show strong downtrend
- Sentiment at extreme greed (contrarian sell)
- High confidence from all analyses

### 4. Risk Assessment

Consider before making recommendations:
- **Volatility**: High volatility = reduce position size
- **Liquidity**: Low liquidity = widen stops, smaller size
- **Time in market**: Newer trends are riskier
- **Correlation**: Diversification reduces risk
- **Black swan risk**: Extreme events possible

### 5. Position Sizing Guidelines

Based on confidence and volatility:
- **High confidence, Low volatility**: Larger positions (up to max allowed)
- **High confidence, High volatility**: Medium positions
- **Medium confidence, Any volatility**: Smaller positions
- **Low confidence**: Minimal or no position

### 6. Entry and Exit Strategy

**Entry Points**
- Strong signals: Enter on market orders or limit near current price
- Medium signals: Enter on pullbacks to support
- Weak signals: Scale in gradually

**Stop Loss Placement**
- Below recent swing low (for longs)
- Above recent swing high (for shorts)
- Below key moving averages
- Account for volatility (wider stops in volatile markets)

**Take Profit Targets**
- First target: 1-2 risk/reward ratio
- Second target: Major resistance/support level
- Final target: Trailing stop to ride trend

### 7. Timeframe Considerations

**Short-term trading (minutes to hours)**
- Focus on 1H and below timeframes
- More sensitive to real-time data and sentiment shifts
- Tighter stops and quicker exits

**Medium-term trading (days to weeks)**  
- Focus on 4H and daily timeframes
- Align with daily trend direction
- Wider stops, let positions breathe

**Long-term trading (weeks to months)**
- Focus on daily and weekly timeframes
- Strong fundamental and macro support needed
- Very wide stops, focus on major trend

### 8. Market Regime Adaptation

**Trending Markets**
- Follow the trend direction
- Use pullbacks for entries
- Trail stops to ride trends
- Ignore minor counter-trend signals

**Ranging Markets**
- Fade extremes (sell highs, buy lows)
- Tighter profit targets
- Avoid trend-following strategies
- Reduce position sizes

**Volatile Markets**
- Wider stops to avoid whipsaws
- Smaller positions
- Quick profit taking
- Consider staying out if too chaotic

## Output Format

When synthesizing into a trading recommendation, provide:
```json
{
  "eval_note": <float -1 to 1>,
  "confidence": <float 0-1>,
  "eval_note_description": "Comprehensive synthesis of all analyses with clear reasoning",
  "key_factors": [
    "Technical: Strong uptrend confirmed",
    "Sentiment: Extreme fear (contrarian buy)",
    "Real-time: Strong buying pressure"
  ],
  "recommended_action": "BUY" | "SELL" | "HOLD",
  "position_size": "FULL" | "MEDIUM" | "SMALL" | "NONE",
  "entry_strategy": "Market order | Limit at X | Scale in on pullback",
  "stop_loss": "Below X at Y",
  "take_profit": ["First: X at R:R 1.5", "Second: Y at resistance", "Final: Trailing stop"]
}
```

## Decision Framework

### Strong Conviction Trade Checklist
- [ ] Multiple timeframes aligned
- [ ] 2+ independent confirmations
- [ ] Clear support/resistance levels identified
- [ ] Sentiment supports the move (or contrarian extreme)
- [ ] Risk/reward ratio > 2:1
- [ ] Market structure supportive
- [ ] Liquidity adequate

### Trade Rejection Criteria
- Mixed signals with no clear edge
- Low confidence across analyses
- Highly uncertain market conditions
- Risk/reward ratio < 1.5:1
- Counter to strong higher timeframe trend
- Illiquid or highly manipulated market

## Best Practices

1. **Never force trades**: Wait for high-probability setups
2. **Quality over quantity**: Fewer high-quality trades beat many mediocre trades
3. **Always know your exit**: Plan stop loss and take profit before entry
4. **Manage risk first**: Protect capital over maximizing gains
5. **Adapt to changing conditions**: What works in trending markets fails in ranging markets
6. **Keep it simple**: Complex strategies with many rules often underperform
7. **Document reasoning**: Track what works and what doesn't
8. **Stay disciplined**: Stick to your strategy and don't chase
9. **Cut losses quickly**: Don't hope losing trades will reverse
10. **Let winners run**: Trail stops on profitable positions

## Common Mistakes to Avoid

- Over-trading in low-conviction setups
- Revenge trading after losses
- Moving stops further away (hoping for reversal)
- Adding to losing positions
- Taking profits too early on winning trades
- Ignoring risk management rules
- Trading against the higher timeframe trend
- Fighting the tape (market momentum)
- Letting emotions override analysis
- Failing to adapt strategy to market regime
