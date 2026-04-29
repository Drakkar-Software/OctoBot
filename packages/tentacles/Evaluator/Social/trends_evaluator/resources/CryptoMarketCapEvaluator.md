Analyzes cryptocurrency market trends through CoinGecko market capitalization data for individual coins.

This evaluator interprets market cap signals from the top 100 cryptocurrencies (ordered by market cap) to produce a normalized score indicating bullish or bearish trends based on:
- Coin position/rank in the top 100 (higher rank = more established)
- Market cap change percentage over 24 hours
- Price change percentage over 24 hours
- Trading volume relative to other top coins

The evaluator generates eval notes by combining these factors with position-based weighting, where higher-ranked coins (e.g., rank 1-10) receive higher confidence multipliers than lower-ranked coins.

Data source: ([CoinGecko API](https://www.coingecko.com/en/api))
