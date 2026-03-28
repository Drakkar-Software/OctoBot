---
title: "Variables d'environnement"
description: "Utilisez des variables d'environnement pour modifier le comportement d'OctoBot. Installez les derniers tentacles, modifiez l'adresse IP et le port de l'interface web, désactivez la limite de taux d'échange, et bien plus encore."
sidebar_position: 10
---



# Les variables d'environnement d'OctoBot

:::info
  La traduction française de cette page est en cours.
:::

## Installation des Tentacles

`TENTACLES_URL_TAG` overrides the default OctoBot version tag for
tentacles package installation. Some additional tags are available :

- **latest** : to install the latest published tentacles (usually requires an up-to-date `dev` branch on OctoBot to work)
- **tests/XXX** : for OctoBot-Tentacles-Manager tests

## Interface Web

- `WEB_ADDRESS` overrides the host IP address, can be set to `0.0.0.0` to accept all incoming connections.
- `WEB_PORT` overrides the default web port (5001).

## Plateformes d'échange

- `DEFAULT_REQUEST_TIMEOUT`: Exchanges requests timeout in milliseconds. Can be increased if your internet connection is very slow. Default value is `20000`.
- `ENABLE_CCXT_VERBOSE`: Set to `True` to log each <a href="https://github.com/ccxt/ccxt" rel="nofollow">ccxt</a> exchange request. Default is `False`.
- `ENABLE_CCXT_RATE_LIMIT`: Set to `False` to disable <a href="https://docs.ccxt.com/#/?id=rate-limit" rel="nofollow">ccxt rate limit</a>. This will make each exchange request to be instantly emitted. **Be careful as this can lead to an IP ban** if the exchange spamming rules are not respected. Default is `True`.
