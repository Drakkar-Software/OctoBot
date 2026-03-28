---
title: "ChatGPT"
description: "Learn how to configure your OctoBot to trade using AI and ChatGPT or another LLM. Understand the costs differences of running it on your local setup."
sidebar_position: 3
---



# Trading with ChatGPT

Seamlessly [Integrate ChatGPT within your trading strategies](/guides/octobot-trading-modes/chatgpt-trading) and profit from the power of AI trading.

<div style="text-align: center">

![octobot collaborating with chatgpt light](/images/guides/interfaces/octobot-collaborating-with-chatgpt-light.png)

</div>

Check out the [ChatGPT trading guide](/guides/octobot-trading-modes/chatgpt-trading) to learn more about how to trade with ChatGPT using OctoBot

OctoBot uses the ChatGPT interface to interact with ChatGPT.

## ChatGPT service configuration

To use ChatGPT on an open source OctoBot, the only configuration you need is to enter your OpenAI API key into the GPT Interface

1. Create or login to your <a href="https://platform.openai.com/" rel="nofollow">OpenAI</a> account
2. Create a new API key on <a href="https://platform.openai.com/account/api-keys" rel="nofollow">your account settings</a>
3. In the Accounts tab of the web interface, add the `GPT` interface if missing 
4. Copy your API key into the `openai-secret-key` GPT configuration

![octobot chatgpt configuration openai key and custom base url](/images/guides/chatgpt/octobot-chatgpt-configuration-openai-key-and-custom-base-url.png)

## Custom LLM base url for prediction

OctoBot can connect to any LLM using the **LLM custom base url** configuration parameter. This is useful to use other AI models than the default OpenAI ones.

In this case, the **Secret key** parameter, will be used to authenticate to this other LLM server when necessary. It will be ignored otherwise.

## Trading with Ollama prediction

To connect to a local Ollama LLM model, configure the **LLM custom base url** of your OctoBot to your Ollama server address followed by `/v1`.

Using the default Ollama address (`localhost:11434`), your **LLM custom base url** would then be: **`http://localhost:11434/v1`**.

## Selecting your LLM model

Selection of the LLM model to use is configured in your GPTEvaluator. When your GPT interface as configured and your `GPTEvaluator` is enabled (when using a ChatGPT-based profile or a custom profile using the `GPTEvaluator`), you can select the LLM model to use from your GPTEvaluator configuration.

The `GPTEvaluator` configuration interface can be accessed from your profile or directly from the `/config_tentacle?name=GPTEvaluator` path of your OctoBot web interface.

## Costs

Using ChatGPT from automated API calls is a paid service from OpenAI. Each call to ChatGPT will consume
a few OpenAI tokens.

Each call to ChatGPT is recrating a request which usually consumes around 90 OpenAI tokens.
You can get the current price of OpenAI token from <a href="https://openai.com/pricing" rel="nofollow">the OpenAI pricing page</a>.

You can estimate the cost of using ChatGPT related features by estimating the amount of requests per day.

> Running a strategy on 4h for 2 trading pairs on 1 exchange: the GPT evaluator will be called every
> 4 hours for each trading pair for each exchange.
