---
title: "Avoir plusieurs OctoBots"
description: "Guide sur comment utiliser plusieurs OctoBots sur le même ordinateur. Utilisez plusieurs comptes sur le même échange et investissez avec plusieurs stratégies"
sidebar_position: 6
---

# Avoir plusieurs OctoBots sur un ordinateur

OctoBot est conçu pour être léger. Bien qu'un OctoBot qui effectue de très nombreuses transactions sur plusieurs crypto et échanges peut nécessiter beaucoup de CPU et de RAM sur votre ordinateur, OctoBot nécessite généralement moins de 1 Go de RAM et 1% de CPU.

Lancer autant d'OctoBot que qu'il vous est nécessaire sur un seul ordinateur est généralement possible, voici comment.

## Comment exécuter plusieurs OctoBot sur un ordinateur ?

Voici les étapes pour démarrer un autre OctoBot sur votre ordinateur :
1. Arrêtez votre OctoBot actuel s'il est en cours d'exécution
2. Dupliquez le dossier entier de votre OctoBot actuel
3. À partir de votre nouveau dossier, démarrez le nouvel OctoBot. Il démarrera à la même adresse web que le bot précédent
4. Changez la valeur du port de l'interface web du nouvel OctoBot (voir le [guide de l'interface web](../octobot-interfaces/web#configuration))
5. Redémarrez votre nouvel OctoBot. Attention : l'adresse de l'interface de votre nouvel OctoBot contiendra désormais la nouvelle valeur du port. Par exemple : si l'adresse de votre premier OctoBot était `http://localhost:5001/`, alors `5001` était son port. Si vous avez utilisé `5002` pour votre autre OctoBot, alors l'adresse de votre autre OctoBot est maintenant `http://localhost:5002/`

Si votre port initial était `5001`, alors en démarrant votre OctoBot initial (à partir du dossier initial), le bot démarrera sur `http://localhost:5001/`. En démarrant votre autre bot, à partir du deuxième dossier, il démarrera sur `http://localhost:5002/`. Les deux bots peuvent être utilisés simultanément et se connecter au compte d'échange de votre choix.

## Pourquoi utiliser un autre dossier et port pour votre OctoBot ?

Chaque OctoBot individuel nécessite seulement deux éléments de votre ordinateur pour fonctionner :
1. **Un dossier dédié pour son exécution**. Cela est nécessaire pour que le bot ait sa propre configuration et gestion des journaux
2. **Un port d'interface web unique**. Deux OctoBots ne peuvent pas utiliser le même port d'interface web. Utiliser la même valeur de port empêchera votre deuxième OctoBot de démarrer son interface web.


## Les bénéfices à utiliser plusieurs OctoBots

Alors qu'un seul OctoBot peut être utilisé pour échanger autant de paires de trading que nécessaire sur plusieurs échanges, l'exécution de plusieurs OctoBots permet de :
- Trader sur plusieurs comptes avec le même échange
- Diviser un portefeuille en différentes cryptos qui seront investies en utilisant différentes stratégies
- Trader à la fois sur les marchés spot et futures sur le même échange
- Utiliser plusieurs stratégies à la fois avec du trading réel et / ou [en trading simulé sans risque](simulator)


## Les limites associées à l'utilisation de plusieurs OctoBots

- Le **rate limit** : Les échanges ont des politiques de rate limit qui peuvent empêcher plusieurs OctoBots fonctionnant à partir de la même adresse IP de récupérer correctement les données des marchés. Lors de l'utilisation de plusieurs OctoBots sur le même échange, il est important de s'assurer de ne pas recevoir d'erreurs liées aux rate limits, sinon votre adresse IP pourrait être temporairement bannie.
- La **bande passante** : L'utilisation de plusieurs OctoBots augmentera la bande passante requise pour récupérer et mettre à jour toutes les données de marché nécessaires. Assurez-vous toujours que votre connexion internet peut gérer cette augmentation correctement, sinon vos stratégies s'exécuteront avec un délai.
- Les **RAM et CPU** : Lors de l'exécution de plusieurs OctoBots sur un ordinateur peu performant or surchargé, vos bots pourraient être ralentis si la RAM ou le CPU sont insuffisants.
