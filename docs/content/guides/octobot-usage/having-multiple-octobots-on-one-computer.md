---
title: "Having multiple OctoBots"
description: "Guide on how to have multiple OctoBots running on the same computer. Use multiple accounts on the same exchange and invest using different strategies."
sidebar_position: 5
---

# Having multiple OctoBots on one computer

OctoBot is designed to be lightweight. While making OctoBot trade on many pairs and exchanges with a very large amount of trades can make it take a lot of CPU and RAM on your computer, OctoBot usually requires less than 1GB of ram and less than 1% of CPU.

Running as many OctoBot as you need on a single computer is most often possible, here is how. 

## How to run many OctoBots on the same computer?

Here are the steps to start another OctoBot on your computer:
1. Stop your current OctoBot if it is running
2. Duplicate the whole folder of your current OctoBot
3. From your new folder, start the new OctoBot. It will start on the same web address as the previous bot
4. Change the new OctoBot web interface port value (see the [web interface guide](../octobot-interfaces/web#configuration))
5. Restart your new OctoBot. Warning: the address of the interface your new OctoBot with now contain the new port value. Example: if your first OctoBot's address was `http://localhost:5001/`, then `5001` was its port. If you used `5002` for your other OctoBot, then your other OctoBot's address is now `http://localhost:5002/`

If your initial port was `5001`, then starting your initial OctoBot (from the initial folder) will start the bot on `http://localhost:5001/`. Starting your other bot, from the second folder, will start on `http://localhost:5002/`. Both bots can be used simultaneously and connect to the exchange account of your choice. 

## Why changing OctoBot port and folder?

Each individual OctoBot requires only two things from your computer in order to run: 
1. **A dedicated folder to be executed into**. This is necessary for the bot to have its own configuration and logs management
2. **A unique web interface port**. Two OctoBots can't use the same web interface port. Using the same port value will prevent your second OctoBot from starting its web interface.

## Benefits of running multiple OctoBots

While a single OctoBot can be used to trade as many trading pairs as needed on multiple exchanges, running multiple OctoBots enables to:
- Trade on many accounts on the same exchange
- Split an account portfolio into assets that can be traded using different strategies
- Trade both spot and futures markets on the same exchange
- Use multiple strategies at once on real and / or [risk-free simulated trading](simulator)

## Limits related to running many bots at once

- **Rate limit**: Exchanges have rate limit policies that can prevent multiple OctoBots running from the same IP address from properly fetching market data. When using multiple OctoBot on the same exchange, it is important to make sure not to receive rate limit related errors, or your IP might get temporarily banned.
- **Bandwidth**: Using multiple OctoBot will increase the required bandwidth to fetch and update all the necessary market data. Always make sure that your internet connection can properly handle this increase, or your strategies will run with a delay.
- **RAM & CPU**: When running multiple OctoBots on a low-end or overloaded computer, your bots might be slowed down if RAM or CPU are insufficient. 
