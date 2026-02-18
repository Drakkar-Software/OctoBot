---
name: market-sentiment
description: Use this skill for analyzing market sentiment from news, social media, fear/greed indices, and overall market mood to assess bullish or bearish conditions.
---

# market-sentiment

## Overview

This skill provides guidance on interpreting market sentiment signals to understand investor psychology and potential market direction. Use this when analyzing sentiment data or gauging market mood.

## Instructions

### 1. Understand Sentiment Indicators

**Fear & Greed Index**
- 0-25: Extreme Fear (potential buy opportunity)
- 25-45: Fear (cautious bullish)
- 45-55: Neutral
- 55-75: Greed (cautious bearish)
- 75-100: Extreme Greed (potential sell opportunity)

**News Sentiment**
- Positive news flow: Bullish sentiment
- Negative news flow: Bearish sentiment
- News saturation: Often marks extremes (contrarian signal)

**Social Media Sentiment**
- High positive sentiment: Bullish, but watch for euphoria
- High negative sentiment: Bearish, but watch for capitulation
- Sentiment spikes often precede reversals

### 2. Identify Sentiment Extremes

Extreme sentiment levels are contrarian indicators:
- **Extreme Fear**: Often marks market bottoms (buy opportunity)
- **Extreme Greed**: Often marks market tops (sell opportunity)
- **Consensus bullishness**: Market may be overbought
- **Consensus bearishness**: Market may be oversold

### 3. Analyze Sentiment Trends

- **Rising bullish sentiment**: Market gaining confidence
- **Declining bearish sentiment**: Market recovering
- **Rising bearish sentiment**: Market losing confidence
- **Declining bullish sentiment**: Market weakening

### 4. Evaluate News Impact

**High Impact News**
- Regulatory announcements
- Major adoption news
- Security breaches
- Economic data releases
- Central bank decisions

**Transient vs Structural News**
- Short-term noise: Price reactions fade quickly
- Fundamental shifts: Long-term impact on valuations

### 5. Social Media Analysis

**Red Flags (Potential Top)**
- Excessive euphoria
- "Get rich quick" narratives spreading
- Retail FOMO (Fear of Missing Out)
- Influencers all bullish

**Green Flags (Potential Bottom)**
- Widespread despair and capitulation
- "Project is dead" narratives
- Retail giving up
- Contrarian voices emerging

### 6. Correlation with Price Action

- **Sentiment leads price**: Strong predictor
- **Sentiment lags price**: Less useful, reaction not prediction
- **Sentiment diverges from price**: Potential reversal signal

## Output Format

When analyzing market sentiment, provide:
```json
{
  "eval_note": <float -1 to 1>,
  "confidence": <float 0-1>,
  "sentiment_summary": "Overall market mood description",
  "key_factors": ["Fear & Greed at 15 (Extreme Fear)", "News sentiment turned positive", "Social media showing capitulation"],
  "description": "Detailed sentiment analysis with reasoning"
}
```

## Sentiment Patterns

**Bullish Sentiment Signals**
- Fear index in extreme fear zone
- Negative news priced in (no reaction to bad news)
- Social media capitulation (everyone giving up)
- Contrarian buying emerging
- Positive news starting to surface

**Bearish Sentiment Signals**
- Greed index in extreme greed zone
- Good news not moving price higher
- Social media euphoria (everyone bullish)
- Mainstream media excitement
- Negative news having outsized impact

## Best Practices

1. Use sentiment as a contrarian indicator at extremes
2. Combine with technical and fundamental analysis
3. Watch for sentiment/price divergences
4. Consider the time horizon (short-term noise vs long-term trend)
5. Distinguish between retail and institutional sentiment
6. Be aware of sentiment manipulation and false narratives
7. Track sentiment changes over time, not just snapshots
8. Consider broader market sentiment, not just asset-specific

## Warning Signs

**Extreme Bull Market Top Indicators**
- "This time is different" narratives
- Parabolic price moves with euphoric sentiment
- Mainstream coverage going viral
- Everyone you know is talking about it
- Extreme leverage and speculation

**Extreme Bear Market Bottom Indicators**
- "It's going to zero" narratives
- Capitulation selling with despair
- Media declaring market dead
- Nobody wants to talk about it anymore
- Forced deleveraging complete
