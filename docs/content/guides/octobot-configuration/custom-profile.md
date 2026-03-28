---
title: "Custom profile"
description: "Lean how to create custom configuration profiles on your OctoBot."
sidebar_position: 5
---



# Custom Profile

A custom profile allow to customize [strategy and trading mode](/guides/octobot-trading-modes/trading-modes).

To create a custom profile :

1. Open an existing profile page
2. Click on duplicate button

![duplicate octobot profile](/images/guides/configuration/duplicate-octobot-profile.png)

## Evaluator and trading configuration

![custom profile trading modes selector](/images/guides/configuration/custom-profile-trading-modes-selector.png)

**user/profiles/profile_name/tentacles_config.json** is a configuration file
telling OctoBot which evaluators, strategies and trading modes to use. It is
kept up to date after each [Tentacle Manager](/guides/octobot-advanced-usage/tentacle-manager)
usage (when new elements become available).

An example of **user/profiles/profile_name/tentacles_config.json** is available <a href="https://github.com/Drakkar-Software/OctoBot-Tentacles/blob/master/profiles/daily_trading/tentacles_config.json" rel="nofollow">as default_tentacles_config.json on github</a>.

![custom profile evaluator selector](/images/guides/configuration/custom-profile-evaluator-selector.png)

## Understanding configuration files

Enabled [evaluators and trading modes](/guides/octobot-trading-modes/trading-modes) are stored in configuration files. You will probably never need to touch them but here is how they work.

Example of **tentacles_config.json**:

```json
{
  "RSIMomentumEvaluator": true,
  "DoubleMovingAverageTrendEvaluator": true,
  "BBMomentumEvaluator": true,
  "MACDMomentumEvaluator": true,
  "CandlePatternMomentumEvaluator": false,
  "ADXMomentumEvaluator": true,

  "InstantFluctuationsEvaluator": true,

  "RedditForumEvaluator": false,
  "GoogleTrendStatsEvaluator": true,

  "TempFullMixedStrategiesEvaluator": true,
  "InstantSocialReactionMixedStrategiesEvaluator": false
}
```

- Here, the first part is about technical analysis evaluators: they are all
  activated except for the **CandlePatternMomentumEvaluator**. This means that
  any technical evaluator of these types (except **CandlePatternMomentumEvaluator**)
  will be used by OctoBot.
- Second part contains only **InstantFluctuationsEvaluator**, OctoBot will
  then take real time market moves into account using **InstantFluctuationsEvaluator** only.
- Third part is the social evaluation. Here OctoBot will look at Google
  stats using **GoogleTrendStatsEvaluator**. However, OctoBot will not look
  a reddit (`"RedditForumEvaluator": false`), therefore
  a [Reddit interface](/guides/octobot-interfaces/reddit) configuration is not necessary.
- Last part are the strategies to use. Here only one strategy out of
  two is to be used by OctoBot: **TempFullMixedStrategiesEvaluator**.

### Details for the devs

Any setting also applies to subclasses of these evaluators. For example
if you add an evaluator extending **ADXMomentumEvaluator**, `"ADXMomentumEvaluator": true`
will tell OctoBot to use the **most advanced ADXMomentumEvaluator** available: if you evaluator
extends **ADXMomentumEvaluator**, your evaluator will be considered more advanced than the **basic
ADXMomentumEvaluator** and OctoBot will use it. See the
developers [customize your OctoBot](/guides/octobot-tentacles-development/customize-your-octobot)
to learn how to add elements to your OctoBot.

This is valid for any evaluator and strategy.

Please note that any evaluator or strategy that doesn't extend
an element in **tentacles_config.json** has to be added to this file otherwise will
be ignored by OctoBot. When using the [Tentacle Manager](/guides/octobot-advanced-usage/tentacle-manager.md)
to install tentacles, this is done automatically.
