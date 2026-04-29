---
title: "Using a proxy"
description: "Use an http or https proxy for your OctoBot connect to your crypto exchange account from a specific IP address or location."
sidebar_position: 3
---



# Using OctoBot with a proxy

## Why using a proxy with your OctoBot

When using OctoBot to automate your investment or trading strategies on your exchange, you might want to use a <a href="https://en.wikipedia.org/wiki/Proxy_server" rel="nofollow">proxy server</a> to emit requests to your exchange from a different IP address or location than the one you are currently at.

This can be relevant in case:

- You wish to enable IP address whitelisting and would like to be sure to always use the same IP address for your OctoBot, even if it changes its location or its server.
- You are traveling somewhere and would like to keep using the IP address for your OctoBot running from your computer.

## How to use OctoBot with an HTTP or HTTPS proxy

To configure your OctoBot to request exchanges from your proxy, configure the following environment variables before starting your [open source OctoBot](../octobot):

- For an HTTP proxy (REST requests): `EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL`
- For an HTTPS proxy (REST requests): `EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL`
- For a SOCKS proxy (websocket connections): `EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL`

Those variable should be configured with your full proxy URL and OctoBot will use it for each of its exchange requests.

Example with a HTTPS proxy:
`EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL=https://username:password@your_proxy.com:8002`

Please note that only one of `EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL` or `EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL` should be set to apply a proxy to your REST requests.
