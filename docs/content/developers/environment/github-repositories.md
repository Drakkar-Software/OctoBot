---
title: "GitHub repositories"
description: "Learn about the different OctoBot repositories on GitHub. How the split is done and what is their purpose."
sidebar_position: 8
---



# OctoBot GitHub repositories

OctoBot code is split into multiple repositories, all hosted under
the <a href="https://github.com/Drakkar-Software" rel="nofollow">Drakkar-Software</a> organisation on
GitHub.

- <a href="https://github.com/Drakkar-Software/OctoBot" rel="nofollow">github.com/Drakkar-Software/OctoBot</a> (dev branch) for the main program initialization,
  backtesting and strategy optimizer setup as well as community data management.
- <a href="https://github.com/Drakkar-Software/OctoBot-Tentacles" rel="nofollow">github.com/Drakkar-Software/OctoBot-Tentacles</a> (dev branch) tentacles: evaluators, strategies, trading
  modes, interfaces, notifiers, external data feeds (reddit, telegram etc),
  backtesting data formats management and exchange specific behaviors.
- <a href="https://github.com/Drakkar-Software/OctoBot-Trading" rel="nofollow">github.com/Drakkar-Software/OctoBot-Trading</a> for everything trading and exchange related: exchange
  connections, exchange data fetch and update, orders, trades and portfolios
  management.
- <a href="https://github.com/Drakkar-Software/OctoBot-evaluators" rel="nofollow">github.com/Drakkar-Software/OctoBot-evaluators</a> for everything related to evaluators and strategies.
- <a href="https://github.com/Drakkar-Software/OctoBot-Services" rel="nofollow">github.com/Drakkar-Software/OctoBot-Services</a> for everything related to interfaces: graphic (web) and
  text(telegram), notifications push and social analysis data management: update
  engine to handle new data from an external feed (ex: reddit) when it gets
  available.
- <a href="https://github.com/Drakkar-Software/OctoBot-Backtesting" rel="nofollow">github.com/Drakkar-Software/OctoBot-Backtesting</a> for the [backtesting
  engine](/en/guides/octobot-usage/backtesting) and scheduling as well as
  historical data collection unified storage management.
- <a href="https://github.com/Drakkar-Software/OctoBot-Tentacles-Manager" rel="nofollow">github.com/Drakkar-Software/OctoBot-Tentacles-Manager</a> for tentacles installation, updates and interactions:
  get a tentacle documentation, configuration or it's dependencies.
- <a href="https://github.com/Drakkar-Software/OctoBot-Commons" rel="nofollow">github.com/Drakkar-Software/OctoBot-Commons</a> for common tools and constants used across each above
  repository.
- <a href="https://github.com/Drakkar-Software/Async-Channel" rel="nofollow">github.com/Drakkar-Software/Async-Channel</a> which is used by OctoBot as a base framework for every
  data transfer within the bot. This allows a highly optimized and scalable
  architecture that adapts to any system while using a very low amount of CPU
  and RAM.
