---
title: "Utiliser un proxy"
description: "Utilisez un proxy HTTP ou HTTPS pour que votre OctoBot se connecte à votre compte d'échange de crypto depuis une adresse IP ou un emplacement prédéfini."
sidebar_position: 3
---



# Utiliser OctoBot avec un proxy

## Pourquoi utiliser un proxy avec votre OctoBot

Lorsque vous utilisez OctoBot pour automatiser vos stratégies d'investissement ou de trading sur votre plateforme d'échange, vous pouvez vouloir utiliser un <a href="https://fr.wikipedia.org/wiki/Proxy" rel="nofollow">proxy</a> pour émettre des requêtes vers votre échange à partir d'une adresse IP ou d'un emplacement différent de celui où vous vous trouvez actuellement.

Cela peut être pertinent dans les cas suivants:

- Vous souhaitez activer le whitelisting des adresses IP et vous aimeriez être certain d'utiliser toujours la même adresse IP pour votre OctoBot, même si votre localisation ou le serveur de votre OctoBot change.
- Vous êtes en déplacement et vous aimeriez continuer à utiliser la même adresse IP pour OctoBot qui s'exécute sur votre ordinateur.

## Comment utiliser OctoBot avec un proxy HTTP ou HTTPS

Pour configurer votre OctoBot pour qu'il fasse ses requêtes vers les échanges depuis votre proxy, configurez les variables d'environnement suivantes avant de démarrer votre [OctoBot open source](../octobot):

- Pour un proxy HTTP (requêtes REST): `EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL`
- Pour un proxy HTTPS (requêtes REST): `EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL`
- Pour un proxy SOCKS (connexions websocket): `EXCHANGE_SOCKS_PROXY_AUTHENTICATED_URL`

Ces variables doivent être configurées avec votre URL de proxy complète et OctoBot l'utilisera pour chacune de ses requêtes vers les échanges.

Exemple avec un proxy HTTPS:
`EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL=https://username:password@your_proxy.com:8002`

Veuillez noter que seul l'une des variables `EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL` ou `EXCHANGE_HTTPS_PROXY_AUTHENTICATED_URL` doit être définie pour appliquer un proxy à vos requêtes REST.
