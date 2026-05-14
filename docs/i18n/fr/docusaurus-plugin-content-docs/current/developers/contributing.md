---
title: "Contribuer"
description: "Comment contribuer à OctoBot. Lignes directrices de développement, style de code et processus de pull request."
keywords: ["contributing", "development", "octobot", "pull request", "guidelines"]
slug: /developers/contributing
sidebar_position: 90
format: md
---

# Contribuer à OctoBot

Vous trouvez qu'il manque une fonctionnalité à OctoBot ? Vos pull requests sont les bienvenues !

Vous découvrez OctoBot ? Voici une [vue d'ensemble de l'architecture du logiciel](https://octobot.cloud/en/guides/octobot-developers-environment/architecture) et voici le [guide développeur](https://octobot.cloud/en/guides/developers).

## Philosophie de développement

OctoBot est multi-stratégie, multi-exchange et multi-cryptomonnaie.
- Toute modification spécifique à une stratégie doit être effectuée dans le code spécifique de cette stratégie, généralement dans un [tentacle](https://github.com/Drakkar-Software/OctoBot-tentacles).
- Toute modification spécifique à un exchange doit être effectuée dans le [tentacle](https://github.com/Drakkar-Software/OctoBot-tentacles) associé à cet exchange.
- Les modifications spécifiques à une cryptomonnaie ou à une paire de trading seront refusées sauf si elles sont justifiées dans le code générique.

## Lignes directrices de contribution

- Créez votre PR sur la branche `dev`, et non `master`, pour les dépôts [OctoBot](https://github.com/Drakkar-Software/OctoBot) et [Tentacles](https://github.com/Drakkar-Software/OctoBot-tentacles) ; créez-les sur `master` pour les autres dépôts.
- Toute modification doit être testée via un ou des tests pytest associés dans le répertoire `tests`.

## Style de code additionnel d'OctoBot

- Toute modification doit être conforme à PEP8 (max-line-length = 120).
- N'utilisez une variable locale que si elle améliore la clarté du code.
- Utilisez toujours des générateurs et des listes en compréhension plutôt que des boucles lorsque c'est possible.
- Utilisez `try ... except` plutôt que des instructions `if` lorsque le `if` est vrai à 99 %.

## Ajout de dépendances

Pour des raisons de sécurité et de maintenance, des dépendances supplémentaires ne peuvent être ajoutées à OctoBot que si elles sont nécessaires au fonctionnement du système global.
Si votre développement nécessite une dépendance externe, veuillez soit :
- Ouvrir une issue pour discuter de l'intégration de cette dépendance dans le code principal.
- Rendre l'import de cette dépendance optionnel dans votre code au moment de l'import, afin que l'OctoBot principal puisse toujours importer votre code et laisser à l'utilisateur la responsabilité d'installer cette dépendance pour utiliser votre code.
