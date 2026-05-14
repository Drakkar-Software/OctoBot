---
title: Trading Backend
description: Couche backend des exchanges gérant l'identification des brokers, la vérification des permissions des clés API et la validation des comptes sur plus de 20 exchanges pris en charge.
sidebar_position: 1
---

# Trading Backend

`trading_backend` est la couche de validation côté exchange qui s'exécute avant le début de tout trading. Son rôle est d'inspecter les permissions des clés API et l'état du compte afin que le reste du système puisse avoir confiance dans le fait que les identifiants dont il dispose sont réellement capables d'effectuer les opérations qu'il a l'intention de réaliser.

## Structure

`Exchange` est la classe de base. Chaque exchange pris en charge possède une sous-classe qui ne surcharge que ce qui diffère du comportement par défaut — la plupart des surcharges sont minimes : une URL de point de terminaison de permissions différente, un code d'erreur différent à interpréter, ou une logique de marquage de broker spécifique à cette plateforme. Une factory sélectionne la bonne sous-classe à l'exécution à l'aide de l'`id` d'exchange de ccxt. Les exchanges non reconnus se rabattent sur la classe de base, qui couvre suffisamment bien le cas courant.

## Détection des permissions

Deux stratégies existent pour détecter ce qu'une clé API est autorisée à faire. Les exchanges qui exposent un point de terminaison de permissions dédié sont interrogés directement. Pour ceux qui ne le font pas, le package utilise une sonde d'annulation : il tente d'annuler un ordre inexistant et interprète la réponse d'erreur. Une erreur de permission signifie que la clé est en lecture seule ; une erreur d'ordre introuvable signifie que les droits de trading sont présents ; une erreur de nonce signale une dérive d'horloge entre le client et le serveur de l'exchange.

Si des droits de retrait sont détectés et que `ALLOW_WITHDRAWAL_KEYS` n'est pas explicitement activé, la clé est rejetée avant le début du trading. Il s'agit d'une mesure de sécurité par défaut — les clés capables de retirer des fonds présentent plus de risques que celles qui ne peuvent que trader, et la plupart des stratégies automatisées n'ont aucune raison d'effectuer des retraits.
