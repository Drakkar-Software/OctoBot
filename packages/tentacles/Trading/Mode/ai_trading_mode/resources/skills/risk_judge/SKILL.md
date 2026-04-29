---
name: risk-judgment
description: Use this skill for objectively evaluating bull vs bear arguments, weighing evidence quality, and providing balanced risk assessments for trading decisions.
---

# risk-judgment

## Overview

This skill provides guidance on objectively evaluating competing bull and bear arguments to determine which case is more compelling. Your role is to be an impartial judge focused on finding truth, not favoring either side.

## Instructions

### 1. Evaluate Evidence Quality

**Strong Evidence**
- Quantitative data from reliable sources
- Historical precedents with similar conditions
- Multiple independent confirmations
- Logical cause-and-effect relationships

**Weak Evidence**
- Anecdotal observations
- Circular reasoning
- Cherry-picked data
- Vague assertions without specifics

### 2. Assess Argument Structure

**Well-Constructed Arguments**
- Clear thesis statement
- Specific, falsifiable claims
- Acknowledges counterarguments
- Provides timeline and magnitude estimates
- Honest about uncertainty

**Poorly-Constructed Arguments**
- Vague or shifting thesis
- Unfalsifiable claims
- Ignores opposing evidence
- Absolute certainty claimed
- No risk acknowledgment

### 3. Weigh Competing Cases

**Evaluation Framework**
```
Bull Score = Evidence_Quality × Argument_Logic × Historical_Support
Bear Score = Evidence_Quality × Argument_Logic × Historical_Support

Winner = Max(Bull_Score, Bear_Score)
Confidence = |Bull_Score - Bear_Score| / Max(Bull_Score, Bear_Score)
```

**Key Decision Factors**
- Which side has stronger evidence?
- Which argument is more logically sound?
- Which historical precedents are more relevant?
- What does the risk/reward asymmetry suggest?
- Which side accounts for more variables?

### 4. Consider Market Regime

**Trending Markets**
- Trend-following arguments weighted higher
- Contrarian arguments need stronger evidence
- Momentum often self-reinforcing

**Ranging Markets**
- Mean-reversion arguments weighted higher
- Breakout arguments need exceptional evidence
- Range extremes offer better risk/reward

**High Volatility**
- Reduce confidence in both arguments
- Increase position size adjustment
- Favor more conservative interpretations

### 5. Risk Assessment

**Overall Risk Categories**
- **Low Risk**: High confidence, strong evidence, clear setup
- **Medium Risk**: Moderate confidence, mixed signals, uncertain timing
- **High Risk**: Low confidence, weak evidence, conflicting data

**Position Size Modifiers**
```
High confidence winner + Low risk = 1.5x position size
High confidence winner + Medium risk = 1.0x position size
High confidence winner + High risk = 0.5x position size
Low confidence / Unclear winner = 0.25x position size or skip
```

## Output Format

```json
{
  "judgment": {
    "winner": "bull",
    "confidence": 0.70,
    "reasoning": "Bull case presents stronger evidence with specific catalysts and clear timeline. Bear case makes valid points about resistance, but lacks concrete negative catalysts. Historical precedent favors bulls at this stage of cycle.",
    "bull_score": 0.75,
    "bear_score": 0.55,
    "key_deciding_factors": [
      "Bull case provides specific, quantifiable catalysts (halving, ETF inflows)",
      "Bear resistance argument weakened by strong volume on recent bounces",
      "Historical data shows current setup preceded rallies 75% of time",
      "Risk/reward favors bulls (3:1 vs 1:1 for bears)"
    ]
  },
  "risk_assessment": {
    "overall_risk": "medium",
    "risk_factors": [
      "Macro uncertainty remains elevated",
      "Technical resistance at 48k not yet broken",
      "Sentiment could shift quickly on negative news"
    ],
    "recommended_position_size_modifier": 0.9
  },
  "additional_notes": "Monitor 48k resistance closely. If broken with volume, confidence in bull case increases to 0.85. If rejected again, reassess bear case."
}
```

## Best Practices

1. **Stay impartial** - Your job is truth-seeking, not picking sides
2. **Quantify when possible** - Use scores and percentages
3. **Explain reasoning** - Make your logic transparent
4. **Acknowledge uncertainty** - Markets are probabilistic, not deterministic
5. **Consider base rates** - What usually happens in similar situations?
6. **Update as new data arrives** - Judgments should evolve
7. **Focus on asymmetry** - Risk/reward often matters more than probability
8. **Favor simplicity** - Complex arguments often hide weaknesses
