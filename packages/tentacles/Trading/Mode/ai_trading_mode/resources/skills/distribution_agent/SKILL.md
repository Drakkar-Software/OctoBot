---
name: portfolio-distribution
description: Use this skill for making final portfolio allocation decisions, determining optimal position sizing, and providing actionable trading recommendations based on risk assessments.
---

# portfolio-distribution

## Overview

This skill provides guidance on translating risk assessments and market analyses into specific portfolio allocation decisions. Your role is to determine optimal position sizes while respecting risk management constraints.

## Instructions

### 1. Position Sizing Framework

**Base Position Size Calculation**
```
Base_Size = Portfolio_Risk_Percentage × (Account_Size / Risk_Per_Trade)
Adjusted_Size = Base_Size × Confidence_Modifier × Risk_Modifier
```

**Confidence Modifiers**
- Very high confidence (>0.85): 1.5x
- High confidence (0.70-0.85): 1.0x
- Medium confidence (0.50-0.70): 0.75x
- Low confidence (<0.50): 0.25x or skip

**Risk Modifiers** (from Risk Judge)
- Low overall risk: 1.2x
- Medium overall risk: 1.0x
- High overall risk: 0.5x

### 2. Portfolio Risk Management

**Total Exposure Limits**
- Maximum total position size: 80% of portfolio
- Single position maximum: 25% of portfolio
- Correlated positions combined: <40% of portfolio
- Reserve minimum: 20% cash for opportunities

**Diversification Rules**
- Don't concentrate >40% in one sector
- Consider correlation between positions
- Balance long and short exposure when appropriate
- Maintain liquidity for rebalancing

### 3. Action Determination

**Buy Actions**
- Bull case won with high confidence
- Current position < target allocation
- Entry zone identified with favorable risk/reward
- Liquidity adequate for execution

**Sell Actions**
- Bear case won with high confidence
- Current position > target allocation
- Stop loss hit or target reached
- Risk/reward deteriorated

**Hold Actions**
- Unclear winner or low confidence
- Current allocation within target range
- Waiting for better entry/exit
- Preserving capital for better opportunities

### 4. Execution Planning

**Priority Ordering**
- Highest conviction trades first
- Most time-sensitive opportunities
- Rebalancing underweight positions
- Taking profits on overweight positions

**Timing Recommendations**
- **Immediate**: High confidence, favorable conditions
- **Limit Order**: Medium confidence, specific entry target
- **Wait**: Low confidence or better setup expected
- **Scale In/Out**: Uncertainty about timing, reduce entry/exit risk

### 5. Trade Structuring

**Entry Strategy**
- Single entry: High confidence, clear signal
- Scaled entry: Medium confidence, want better average
- Layered limit orders: Range-bound market
- Market order: Time-sensitive, high urgency

**Exit Strategy**
- Initial stop loss: Below key support (long) or above resistance (short)
- First target: 1.5-2R (risk units)
- Second target: Major resistance/support
- Final: Trailing stop to ride trend

## Output Format

```json
{
  "distribution": {
    "allocations": [
      {
        "symbol": "BTC/USDT",
        "action": "buy",
        "current_percentage": 10.0,
        "target_percentage": 18.0,
        "quantity_change": 0.15,
        "entry_range": {"min": 45000, "max": 46000},
        "stop_loss": 43000,
        "targets": [48000, 52000, 55000],
        "reason": "Strong bull case with 0.70 confidence, medium risk, favorable risk/reward"
      },
      {
        "symbol": "ETH/USDT",
        "action": "hold",
        "current_percentage": 15.0,
        "target_percentage": 15.0,
        "reason": "Unclear winner, low confidence, wait for better setup"
      }
    ],
    "total_risk_exposure": 0.65,
    "cash_reserve": 0.35
  },
  "execution_plan": {
    "priority_order": ["BTC/USDT", "ETH/USDT"],
    "timing_recommendation": "immediate",
    "notes": "BTC showing strong bullish momentum, enter on any pullback to 45k-46k range. Set stops below 43k. Scale out at targets."
  },
  "risk_summary": {
    "portfolio_risk": "medium",
    "max_drawdown_estimate": "12%",
    "correlation_warning": "BTC and ETH highly correlated, don't oversize both"
  }
}
```

## Best Practices

1. **Never overleverage** - Respect maximum position sizes
2. **Always define stops** - Know your exit before entry
3. **Scale positions by conviction** - Higher confidence = larger size
4. **Consider correlation** - Don't concentrate risk
5. **Maintain reserves** - Keep cash for opportunities
6. **Document decisions** - Save to /memories/distributions/ for review
7. **Review regularly** - Rebalance as conditions change
8. **Risk first, returns second** - Preserve capital above all

## Common Mistakes to Avoid

- Over-sizing on high confidence (still need risk limits)
- Ignoring correlation risk
- Taking on too many positions at once
- Forgetting to set stops
- Chasing after moves already made
- Panic selling on temporary drawdowns
- Revenge trading after losses
