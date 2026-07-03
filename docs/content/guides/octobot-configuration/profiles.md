---
title: "Profiles"
description: "What is an OctoBot profile ? OctoBot is configured using profiles, where your configuration for a specific trading strategy is saved and can be shared."
sidebar_position: 1
---

# Profiles

OctoBot's trading configuration is using profiles. This allows for quick switches between previously set
configurations. Each profile defines a [Trading Mode](/guides/octobot-trading-modes/trading-modes) configuration as well as other settings.

Bundled default profiles (for example `default` and `non-trading`) remain on the filesystem under
`user/profiles/`. When a wallet is configured, user-created profiles are stored in the sync
`StrategyProvider` collection as `GenericProcessConfiguration.profile_data` (same profile id as the
strategy). OctoBot still exposes the same profile API to the web UI and configuration layer; only the
profile module selects the storage backend.

![octobot trading mode details from profiles](/images/guides/configuration/octobot-trading-mode-details-from-profiles.png)

Profiles include:

-   Tentacles activations
-   Tentacles configurations
-   Traded pairs
-   Enabled exchanges
-   Trading configuration
-   Automation configuration

Login related data (exchange api keys, telegram settings, ...) are not stored in profiles.


Profiles can also be [shared and imported](sharing-and-importing-octobot-profiles) between OctoBot's users.
