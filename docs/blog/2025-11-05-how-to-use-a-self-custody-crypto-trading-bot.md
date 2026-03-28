---
title: "How to use a self custody crypto trading bot"
description: "Learn how to use a self custody crypto trading bot to automate your investment strategies on centralized and decentralized exchanges."
slug: "how-to-use-a-self-custody-crypto-trading-bot"
date: "2025-11-05"
authors: ["guillaume"]
tags: ["Trading", "Exchange", "Self custody", "Crypto"]
image: "/images/blog/how-to-use-a-self-custody-crypto-trading-bot/not-your-keys-not-your-coins-writen-on-paper-with-keys-and-a-bitcoin-logo.png"
---



  BarChart,
  CheckCircle,
  CircleDollarSign,
  Globe,
  Shield,
  TrendingUp,
  Zap,
} from 'lucide-react'

# How to use a self custody crypto trading bot


<div style={{textAlign: "center"}}>
  <div>
    ![chatgpt-logo](/images/blog/how-to-use-a-self-custody-crypto-trading-bot/not-your-keys-not-your-coins-writen-on-paper-with-keys-and-a-bitcoin-logo.png)
    _"Not your keys, not your coins"_
  </div>
</div>

<!--truncate-->

This is one of the core principles of crypto: self custody of your crypto assets guarantees the security and independence provided by blockchain technology. 

- First, it started with wallets such as <a href="https://metamask.io/" rel="nofollow">MetaMask</a> or <a href="https://electrum.org/" rel="nofollow">Electrum</a> to give you full control over your crypto assets.
- Then decentralized exchanges such as <a href="https://app.uniswap.org/" rel="nofollow">Uniswap</a> allowed to easily trade your crypto assets without having to trust a central authority.
- Decentralized exchanges continued to improve and now also propose sophisticated trading instruments such as perpetual futures on <a href="https://app.hyperliquid.xyz/" rel="nofollow">Hyperliquid</a>.

Finally, self custody trading bots, allowing to leverage crypto exchanges to automate investment strategies independently from any centralized authority, are starting to appear.

## What is a non custodial crypto trading bot
A non custodial crypto trading bot is a trading bot that is fully controlled by you, its user.
1. It is not controlled by a central authority such as a crypto exchange or a trading bot platform that holds your API (or wallet) keys. 
2. It's a trading robot that lets you have custody of your exchange API keys or crypto wallet.


While self custody is a core principle of crypto, it is not always easy to implement.  
To achieve it, you need to configure your own wallet, which can be quickly done on a browser wallet such as <a href="https://metamask.io/" rel="nofollow">MetaMask</a>. This wallet can then be used to store your crypto and exchange them on decentralized exchanges.


<div style={{textAlign: "center"}}>
  <div>
    ![metamask-logo](/images/blog/how-to-use-a-self-custody-crypto-trading-bot/metamask-logo.png)
  </div>
</div>


From this point, a trading bot connected to this wallet will be able to apply your investment strategy by trading your crypto on decentralized exchanges using your own wallet.

This implies that the bot will access your crypto wallet directly, which means that you need to have a very high trust in the bot platform you are using. The risk being that any hacker compromising the bot platform will be able to steal your crypto.

Here is where a self custody crypto trading bot comes in. It is a trading bot that is only controlled by you, it never shares your crypto wallet's keys with any platform or anyone.  


A self custody crypto trading bot can connect to both centralized and decentralized exchanges, and in both cases, it greatly increases the security of your crypto assets.


### Self custody crypto trading bot for centralized exchanges

To automate a strategy on a centralized exchange, there are three main options:

**Simple but rigid:** centralized exchange built-in trading bot services  
In this case, the bot is running <a href="https://www.binance.com/trading-bots" rel="nofollow">directly on the centralized exchange servers</a>. This has the advantage of being secure and very easy to setup and use, but it also has the drawbacks of lacking the flexibility of a specialized trading bot tools.

**Flexible but less secure:** specialized trading bot platforms  
The bot is running on the servers of a trading bot platform such as <a href="https://3commas.io/" rel="nofollow">3Commas</a>. This has the advantage of being flexible and allowing to use a lot of different trading strategies, but it also has the drawbacks of being less secure as the bot platform can <a href="https://blockworks.co/news/3commas-security-breach" rel="nofollow">leak your API keys</a> in case of a security breach.

**Secure and flexible:**  self custody crypto trading bots  
A bot, such as [the open source version of OctoBot](https://www.octobot.cloud/trading-bot), is running on your own computer or server. Your API keys never leave your device. This has the advantage of being secure and flexible, but it also has the drawbacks of being more complex to setup and use.

As often, there is no "one size fits all" solution. You need to choose the best solution for your needs. The interesting part being the fact that there are more and more [secure and flexible options](https://www.octobot.cloud/features/self-custody-trading-bot) available as self custody trading bots are becoming more accessible to the general public.

### Self custody crypto trading bot for decentralized exchanges

To automate a strategy on a decentralized exchange, there are two main ways of running a DEX bot:

**Trusting a DEX trading bot platform**  
In this case, the bot is running on the servers of the DEX bot platform . While this is convenient, as it implies sharing your wallet with the platform, any issue with this platform can have devastating consequences for your funds.

**Self custody crypto trading bots**  
This bot runs on your device and never shares your wallet with any platform, making it by far the most secure option. Drawback being that very few trading bots are available for decentralized exchanges.

Overall, automating an investment strategy on a DEX is still very challenging, that's why we are working on an easy to use [self custody crypto trading bot for decentralized exchanges](https://www.octobot.cloud/features/self-custody-trading-bot).

### Pros and cons of self custody crypto trading bots


The only way use a self custody crypto trading bot is to run it on your own computer or server. Its usually means a desktop application that you install on your system and a lot of headaches to setup and run properly.

**Advantages of self custody crypto trading bots**

<div>
  {[
    {
      icon: <CheckCircle className="text-primary" />,
      name: 'Your keys, your coins',
      description: 'You are the only one who has access to your crypto wallet',
    },
    {
      icon: <Shield className="text-primary" />,
      name: 'Best security',
      description: 'There is no third party to compromise your crypto or API keys',
    },
    {
      icon: <CircleDollarSign className="text-primary" />,
      name: 'Highest flexibility',
      description: 'Use decentralized and centralized exchanges from the same platform',
    },
  ].map((element, i) => (
    <HighlightElement key={i} element={element} />
  ))}
</div>

**Drawbacks of self custody crypto trading bots**

<div>
  {[
    {
      icon: <CircleDollarSign className="text-rating-color-2" />,
      name: 'Responsibility',
      description: 'You are responsible of your crypto wallet and API keys security, there is no recovery service if you lose your keys.',
    },
    {
      icon: <Globe className="text-rating-color-2" />,
      name: 'Running the software',
      description:
        'The software needs to continuously be executed on your own computer or server.',
    },
    {
      icon: <Globe className="text-rating-color-2" />,
      name: 'Complex setup',
      description:
        'A self custody crypto trading bot usually requires technical knowledge and a secure setup.',
    },
  ].map((element, i) => (
    <HighlightElement key={i} element={element} />
  ))}
</div>

At OctoBot, we are working on a self custody crypto trading bot that solves both the **Running the software** and **Complex setup** drawbacks using a secure self-custody trading bot from your mobile phone.

<div style={{textAlign: "center"}}>
  **[Register to the early access](https://www.octobot.cloud/features/self-custody-trading-bot)**
</div>


## How to use a self custody crypto trading bot

A self custody crypto trading bot is always a software you need to install, configure and run on your own mobile, computer or server.

First step is then to download and install a self custody crypto trading bot, such as the [OctoBot open source trading bot desktop application](https://www.octobot.cloud/trading-bot).

Then, you will be able to select the strategy you want to use, connect to your exchange account and start trading.  
While OctoBot works with most centralized exchanges and a few decentralized exchanges, if your primary goal is to trade on decentralized exchanges, you might want to use a specialized bot such as <a href="https://hummingbot.org/" rel="nofollow">Hummingbot</a>.  
That's it, your bot is installed and configured, this was the easy part. 

> "Installing a self custody crypto trading bot is simple. Properly running and securing it is not."

Your self custody crypto trading bot is now automating your strategy. Next steps are to:
- Make sure it runs 24/7 (which means monitoring, restarting it if it crashes, keeping it updated)
- Keep it secure against other people accessing your computer, potential malwares and security breaches.
- If it runs on a server, make sure your connection to it is secure and encrypted at all times.

This can be a real challenge, especially if you are not a person with a strong technical background. This is why until today, the vast majority of self custody crypto trading bots were only available as desktop applications (or even command line tools) designed for highly technical users.


## A self custody crypto trading bot mobile app

At OctoBot, we have been working on trading bots since 2018, the year we coded the first version of the <a href="https://github.com/Drakkar-Software/OctoBot" rel="nofollow">open source OctoBot on GitHub</a>. Time has passed since then and the crypto world has changed a lot.  
With the rise of popular decentralized exchanges such as Hyperliquid or Uniswap and stricter and stricter regulations, traditional trading bot platforms are, in many cases, not the obvious choice anymore.

This is why we have been working on a **self custody crypto trading bot mobile app** that allows you to:
- **Automate your investment strategies** on your centralized and decentralized exchanges **in a simple way**.
- **Secure your crypto wallet and centralized exchange API keys** on your own device.
- Profit from your **mobile phone accessibility** to always have control over your investment strategies.

We will be launching the app very soon. Register to the early access to be the first to use it.

<div style={{textAlign: "center"}}>
  **[Register to the early access](https://www.octobot.cloud/features/self-custody-trading-bot)**
</div>
