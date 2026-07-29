---
title: "GitHub repositories"
description: "Learn about the OctoBot monorepo on GitHub. How the code is split into packages and what is their purpose."
sidebar_position: 8
---



# OctoBot GitHub repository

OctoBot code lives in a single Python monorepo, hosted under
the <a href="https://github.com/Drakkar-Software" rel="nofollow">Drakkar-Software</a> organisation on
GitHub: <a href="https://github.com/Drakkar-Software/OctoBot" rel="nofollow">github.com/Drakkar-Software/OctoBot</a> (dev branch for development, master branch for the stable version).

The repository root holds the main program initialization and community data management. Everything else is
split into packages, each dedicated to a different aspect of the software, in its own folder under `packages`.
Packages are built with <a href="https://www.pantsbuild.org/" rel="nofollow">Pants</a> and
declared in the `root_patterns` of the `pants.toml` file at the root of the repository.

Each of these packages used to be a separate GitHub repository. Those repositories are now archived and
read only, all the development happens in the monorepo.

- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/trading" rel="nofollow">packages/trading</a> for everything trading and exchange related: exchange
  connections, exchange data fetch and update, orders, trades and portfolios
  management.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/evaluators" rel="nofollow">packages/evaluators</a> for everything related to evaluators and strategies.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/services" rel="nofollow">packages/services</a> for everything related to interfaces: graphic (web) and
  text(telegram), notifications push and social analysis data management: update
  engine to handle new data from an external feed (ex: reddit) when it gets
  available.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/backtesting" rel="nofollow">packages/backtesting</a> for the [backtesting
  engine](/en/guides/octobot-usage/backtesting) and scheduling as well as
  historical data collection unified storage management.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/tentacles" rel="nofollow">packages/tentacles</a> tentacles: evaluators, strategies, trading
  modes, interfaces, notifiers, external data feeds (reddit, telegram etc),
  backtesting data formats management and exchange specific behaviors. This is the source of the
  tentacles, the `tentacles` folder used by a running OctoBot is generated from it.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/tentacles_manager" rel="nofollow">packages/tentacles_manager</a> for tentacles installation, updates and interactions:
  get a tentacle documentation, configuration or it's dependencies.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/commons" rel="nofollow">packages/commons</a> for common tools and constants used across each other
  package.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/async_channel" rel="nofollow">packages/async_channel</a> which is used by OctoBot as a base framework for every
  data transfer within the bot. This allows a highly optimized and scalable
  architecture that adapts to any system while using a very low amount of CPU
  and RAM.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/agents" rel="nofollow">packages/agents</a> for the AI agents of OctoBot: individual agents, agent
  teams and their storage.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/copy" rel="nofollow">packages/copy</a> for copy trading: order mirroring and portfolio
  rebalancing to replicate a followed account.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/flow" rel="nofollow">packages/flow</a> for the OctoBot automations runner: the jobs, parsers and
  logic behind automations.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/node" rel="nofollow">packages/node</a> for OctoBot Node, which allows running any OctoBot anywhere
  as a remotely managed service.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/protocol" rel="nofollow">packages/protocol</a> for the data shapes shared across OctoBot runtimes
  (accounts, orders, trades, automations and their enums). They are generated from an OpenAPI document
  into Python, TypeScript and Rust models.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/sync" rel="nofollow">packages/sync</a> for the server component that lets OctoBot nodes act as
  personal sync endpoints, including its wallet based authentication and encrypted user data collections.
- <a href="https://github.com/Drakkar-Software/OctoBot/tree/master/packages/binary" rel="nofollow">packages/binary</a> to create and upload the Windows, Linux and MacOS
  binaries of each OctoBot release.
