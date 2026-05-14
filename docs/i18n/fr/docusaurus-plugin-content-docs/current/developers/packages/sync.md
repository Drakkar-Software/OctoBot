---
title: Sync
description: Serveur et client de synchronisation authentifiés cryptographiquement pour le partage de données entre instances OctoBot, construits sur FastAPI et le framework Starfish.
sidebar_position: 1
---

# Sync

`octobot_sync` est le serveur et le client de synchronisation d'OctoBot. Il permet à plusieurs instances OctoBot de partager des collections de données — configurations de bots, comptes, signaux, métadonnées de produits — via HTTPS, chaque requête étant authentifiée par une signature de wallet EVM et chaque payload stocké étant chiffré au repos.

## Architecture

Le package est construit au-dessus de [Starfish](https://github.com/Drakkar-Software/starfish-server), qui fournit la machinerie générique de routage des collections, de contrôle d'accès basé sur les rôles, de chiffrement et de synchronisation des réplicas. `octobot_sync` apporte la couche spécifique à OctoBot : le schéma d'authentification basé sur EVM, le registre de chaînes pour la résolution de propriété on-chain, les définitions de collections et les points d'entrée de l'application. Cette séparation signifie que la machinerie de base du serveur de synchronisation n'est pas spécifique à OctoBot et peut être réutilisée ailleurs, tandis que les collections et les règles d'authentification vivent là où elles peuvent évoluer avec le produit.

Un déploiement de synchronisation peut fonctionner selon deux modes. Un **serveur primaire** est adossé à un stockage d'objets compatible S3 et constitue la source de vérité canonique. Un **serveur réplica** est adossé à un stockage sur système de fichiers local et reflète un sous-ensemble des collections du primaire à l'aide du `ReplicaManager` de Starfish. Le point d'entrée client `create_sync_client` gère les deux : il renvoie un client connecté et peut éventuellement démarrer un serveur réplica local dans un thread démon avant de s'y connecter, de sorte qu'une instance OctoBot puisse travailler sur une copie locale à proximité.

## Authentification

Chaque requête transporte cinq en-têtes HTTP : l'adresse EVM de l'appelant, une signature EIP-191 de type personal-sign, un horodatage Unix en millisecondes, un nonce UUID et l'identifiant de chaîne au format `evm:<chainId>`. Le serveur construit une chaîne canonique à partir de la méthode, du chemin, de l'horodatage, du nonce et du SHA-256 du corps de la requête, puis vérifie la signature par rapport à cette chaîne. Les horodatages sont vérifiés à ±10 secondes près de l'heure du serveur, et les nonces sont suivis pendant 30 secondes pour empêcher les attaques par rejeu. Un appelant dont l'adresse correspond à `PLATFORM_PUBKEY_EVM` reçoit le rôle d'administrateur ; tous les autres appelants valides reçoivent le rôle d'utilisateur.

Lorsqu'une requête transporte un paramètre de chemin `productId`, un enrichisseur de rôles s'exécute et interroge les chaînes enregistrées pour connaître la propriété et les droits d'accès on-chain. Posséder un produit accorde les rôles de propriétaire et de membre ; disposer d'un accès n'accorde que le rôle de membre. Ce sont ces rôles qui déterminent quelles collections l'appelant peut lire ou écrire, rendant le contrôle d'accès piloté par les données plutôt que codé en dur.

## Collections

Une collection est l'unité de stockage. Chacune définit un modèle de chemin de stockage, des exigences de rôle en lecture/écriture, un mode de chiffrement et des contraintes optionnelles sur la taille, le schéma, le type MIME et la limitation de débit. Le modèle de chemin (par exemple `users/{identity}` ou `items/{itemId}/feed/{version}`) joue un double rôle : il détermine où les données sont stockées et si la collection est réplicable. Les variables de modèle rendent une collection non réplicable, car il n'existe pas de chemin canonique unique depuis lequel le réplica peut tirer les données.

Lorsqu'aucun `collections.json` n'est présent, le package se rabat sur une configuration par défaut couvrant les collections de bots, de comptes et d'erreurs, avec des paramètres de rôle et de chiffrement appropriés.

## Couche on-chain

La couche de chaînes fournit une interface abstraite pour le support multi-chaînes ainsi qu'une implémentation EVM ciblant Base. Les appels on-chain sont mis en cache avec une TTL pour éviter de surcharger le point de terminaison RPC : la propriété est mise en cache pendant un an puisqu'elle est traitée comme immuable, les droits d'accès pendant 60 secondes, et les recherches d'éléments pendant 30 secondes. Les niveaux de cache reflètent la fréquence à laquelle chaque donnée change en pratique.

## Synchronisation des réplicas

Seules les collections dont le chemin de stockage ne contient aucune variable de modèle peuvent être répliquées, puisque la réplication requiert un unique chemin de tirage canonique. Chaque collection réplicable se voit injecter des chemins de tirage et de poussée ainsi que des déclencheurs de synchronisation — au tirage et planifiés — afin que le réplica reste à jour à la fois de manière réactive et selon un minuteur. Les requêtes sortantes du réplica vers le primaire sont authentifiées à l'aide du même schéma de signature EVM via `StarfishAuthProvider`.

## Intégration nginx

Le package peut générer une configuration de reverse-proxy nginx à partir d'un `collections.json`. Les collections publiques en lecture seule reçoivent un cache de proxy d'une heure ; les collections publiques accessibles en écriture reçoivent un cache de 30 secondes ; toutes les autres collections sont relayées directement sans mise en cache. Les collections pour lesquelles la limitation de débit est activée reçoivent une zone stricte de limitation de débit sur les chemins de poussée. Cela maintient automatiquement la configuration nginx en cohérence avec la sémantique des collections, plutôt que d'exiger un alignement manuel entre les deux.
