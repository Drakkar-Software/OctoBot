---
title: Node
description: OctoBot Node — un serveur d'exécution de tâches durable qui exécute les automatisations d'OctoBot via un backend FastAPI et un ordonnanceur propulsé par DBOS.
sidebar_position: 1
---

# OctoBot Node

Le package `node` est un service autonome qui exécute les automatisations d'OctoBot sous forme de tâches durables et distribuées. Il fait tourner une application FastAPI adossée à [DBOS](https://docs.dbos.dev/) — un moteur de workflow qui persiste en base de données chaque étape de chaque exécution, rendant le node résilient aux crashs et sûr à redémarrer en cours de tâche.

## Ce que fait un node

Un node reçoit des tâches d'automatisation via son API REST et WebSocket, les stocke dans SQLite ou PostgreSQL, et les transmet au runtime `octobot_flow` pour exécution. Chaque tâche décrit un DAG d'actions. Le node gère l'ordonnancement, les retries, la récupération après crash et l'isolation des logs par workflow. Les payloads de tâches peuvent éventuellement être chiffrés de bout en bout.

Une instance peut jouer un ou plusieurs rôles : elle peut accepter et ordonnancer des tâches (master), les tirer et les exécuter (consumer), ou les deux. C'est le fait de les exécuter séparément qui permet à la couche consumer de monter en charge indépendamment. Les déploiements multi-nodes nécessitent une base de données PostgreSQL partagée ; SQLite est limité à un seul node.

## Cycle de vie d'un workflow

DBOS persiste en base de données chaque invocation de workflow et chaque résultat d'étape. Si le processus crashe en cours d'exécution, le workflow reprend à partir de la dernière étape terminée plutôt que de tout recommencer. Chaque itération d'automatisation s'exécute comme un workflow enfant distinct — un choix de conception délibéré qui empêche une automatisation longue d'accumuler un historique d'étapes illimité dans un unique enregistrement de workflow. Les identifiants des workflows enfants intègrent l'UUID4 parent comme préfixe, de sorte que l'API puisse les regrouper en un historique d'exécution cohérent.

La fonction `execute_iteration` est elle-même une étape DBOS plutôt qu'un simple appel asynchrone. C'est ce qui empêche la double exécution : DBOS enregistre atomiquement l'entrée et la sortie de l'étape, de sorte qu'un crash entre ces deux points rejoue l'étape plutôt que de l'exécuter une seconde fois. Les étapes sont retentées jusqu'à trois fois avant que le workflow ne se termine en erreur.

Les actions déclenchées par l'utilisateur — par exemple une surcharge manuelle envoyée via l'API — sont délivrées sous forme de messages DBOS sur le topic `"user_actions"` pendant que le workflow s'exécute. Cela leur permet de contourner l'étape suivante planifiée du DAG et d'être traitées comme des itérations supplémentaires immédiatement après la fin de l'itération courante.

Les messages de log émis à l'intérieur de n'importe quel workflow ou étape sont routés vers un fichier par workflow sous `logs/automations/`. Les workflows enfants partagent le fichier de log de leur parent, indexé par les 36 premiers caractères de l'identifiant du workflow.

## Chiffrement

Les payloads de tâches sont optionnellement chiffrés à l'aide d'un schéma hybride RSA/AES-GCM/ECDSA. Chaque appel de chiffrement génère une nouvelle clé AES-256-GCM et un nouvel IV ; la clé AES est enveloppée avec RSA-OAEP afin que le payload volumineux ne voyage jamais directement sous la clé asymétrique. Une signature ECDSA sur le texte chiffré — calculée comme la concaténation `ciphertext + encrypted_aes_key + iv` — est vérifiée avant toute tentative de déchiffrement, empêchant les attaques à texte chiffré choisi.

**Modèle de clés à propriété partagée.** Le serveur détient deux clés privées définies via des variables d'environnement :

| Variable d'environnement | Rôle |
|---|---|
| `TASKS_SERVER_RSA_PRIVATE_KEY` | Déchiffre le contenu des tâches entrantes (clé AES enveloppée) |
| `TASKS_SERVER_ECDSA_PRIVATE_KEY` | Signe les résultats de tâches sortants |

Le navigateur détient deux clés privées, saisies une seule fois dans la page Paramètres et stockées localement :

| Clé du navigateur | Rôle |
|---|---|
| `USER_RSA_PRIVATE_KEY` | Déchiffre le contenu des résultats provenant du serveur |
| `USER_ECDSA_PRIVATE_KEY` | Signe le contenu des tâches avant soumission |

Les clés publiques de l'utilisateur ne sont pas configurées sur le serveur. Lorsque le navigateur soumet une tâche chiffrée, il dérive les deux clés publiques à partir des clés privées stockées à l'aide de la Web Crypto API. La clé publique ECDSA est intégrée au payload de la tâche (`user_ecdsa_public_key`) afin que le serveur puisse vérifier la signature d'entrée chaque fois que cette tâche est consommée. La clé publique RSA n'est pas stockée avec la tâche ; à la place, le navigateur la dérive à neuf et l'inclut dans chaque requête d'export des résultats, afin que le serveur puisse envelopper la clé AES spécifiquement pour l'utilisateur demandeur. Cette séparation signifie que la clé ECDSA est liée au moment où une tâche a été créée, tandis que la clé de chiffrement RSA est toujours la clé actuelle de l'utilisateur — la rotation des clés est prise en charge de façon transparente, sans resoumettre de tâches.

Les clés publiques du serveur (`SERVER_RSA_PUBLIC_KEY` et `SERVER_ECDSA_PUBLIC_KEY`) ne sont jamais saisies manuellement — le navigateur les récupère à la demande depuis `GET /tasks/server-public-keys`, qui les dérive et les renvoie à partir des clés privées du serveur à l'exécution. Le serveur ne charge jamais les clés privées de l'utilisateur ; le navigateur ne charge jamais les clés privées du serveur.

**Chiffrement dans le navigateur.** Lors de la soumission de tâches chiffrées, le navigateur effectue toutes les opérations cryptographiques localement à l'aide de la Web Crypto API (`crypto.subtle`), sans envoyer aucun matériel de clé au serveur. La fonction `encryptAndSign` récupère d'abord la clé publique RSA du serveur depuis `GET /tasks/server-public-keys`, génère une nouvelle clé AES-256-GCM, chiffre le payload de la tâche, enveloppe la clé AES avec cette clé publique RSA du serveur (RSA-OAEP), puis signe la concaténation du texte chiffré, de la clé enveloppée et de l'IV avec `USER_ECDSA_PRIVATE_KEY`. La signature ECDSA est convertie du format IEEE P1363 produit par Web Crypto vers le format DER avant transmission, car la bibliothèque `cryptography` de Python attend du DER.

**Format des métadonnées.** L'enveloppe de métadonnées qui accompagne la tâche transporte `ENCRYPTED_AES_KEY_B64`, `IV_B64` et `SIGNATURE_B64`. Pour les entrées de tâches, `content_metadata` est du `base64(JSON)` — l'objet JSON est sérialisé puis encodé en base64 — car il voyage en tant que champ CSV ou champ d'API où une unique chaîne opaque est la plus simple à intégrer. Pour les résultats de tâches, `result_metadata` est une simple chaîne JSON ; elle est stockée en base de données et consommée par du code qui gère déjà le JSON, de sorte que la couche base64 supplémentaire ne serait que du bruit. Avoir conscience de cette distinction importe lorsqu'on construit un outillage qui lit les enregistrements bruts de la base de données.

**Gestionnaire de contexte `encrypted_task`.** Celui-ci encapsule de façon transparente chaque exécution de tâche sur le node consumer. À l'entrée, il déchiffre `task.content` à l'aide de `TASKS_SERVER_RSA_PRIVATE_KEY` et vérifie la signature lorsque `task.content_metadata` est non nul. La vérification de signature utilise d'abord le propre champ `user_ecdsa_public_key` de la tâche (les tâches soumises par le navigateur le transportent en ligne) ; en son absence, elle se rabat sur la variable d'environnement `TASKS_USER_ECDSA_PUBLIC_KEY` ; puis elle se rabat sur la propre clé publique ECDSA du serveur (état interne généré par le serveur, signé avec `TASKS_SERVER_ECDSA_PRIVATE_KEY`). Si le déchiffrement échoue, le gestionnaire de contexte journalise l'erreur et poursuit avec le contenu chiffré d'origine — il ne fait pas planter le workflow. À la sortie, il restaure le `task.content` d'origine et ne touche pas aux résultats.

**Chiffrement de l'état interne et des résultats.** Entre les itérations, l'état de l'automatisation est stocké dans DBOS, chiffré avec `encrypt_task_content` (AES-GCM enveloppé avec SERVER_RSA_PUBLIC, signé avec SERVER_ECDSA_PRIVATE), ce qui le rend lisible uniquement par le serveur. Lorsque l'utilisateur exporte explicitement des résultats terminés, le navigateur inclut sa clé publique RSA PEM actuelle dans le corps de la requête d'export des résultats. L'ordonnanceur déchiffre l'état stocké à l'aide du gestionnaire de contexte `encrypted_task` (SERVER_RSA_PRIVATE + clé publique ECDSA SERVER/USER), puis le re-chiffre avec `encrypt_task_result` (AES-GCM enveloppé avec la clé publique RSA fournie dans la requête, signé avec SERVER_ECDSA_PRIVATE) avant de le renvoyer. Si aucune clé publique RSA n'est fournie dans la requête, l'ordonnanceur renvoie l'état déchiffré en clair. Le déchiffrement a lieu dans le navigateur à l'aide de `USER_RSA_PRIVATE_KEY`, la signature étant vérifiée par rapport à `SERVER_ECDSA_PUBLIC_KEY`. Comme la clé RSA provient de la requête plutôt que de la tâche, un utilisateur qui effectue une rotation de ses clés ou qui exporte une tâche initialement soumise sans chiffrement reçoivent tous deux des résultats correctement chiffrés sans rien resoumettre.

**Frontière de sécurité avec `octobot_flow`.** Le gestionnaire de contexte `encrypted_task` encapsule l'appel à `AutomationJob.run()` d'`octobot_flow` à l'intérieur de l'étape de workflow du node. Le contenu de la tâche est déchiffré juste avant l'exécution sur le node consumer qui détient les clés privées du serveur. Du point de vue de flow, rien ne change — il reçoit un dictionnaire `AutomationState` en clair et en renvoie un mis à jour. Le package flow n'a aucune connaissance du chiffrement, ce qui signifie que le même moteur fonctionne de façon identique dans les déploiements de nodes chiffrés, les nodes non chiffrés et les bots autonomes.

**Chargement et validation des clés.** Les deux clés du serveur sont acceptées sous forme de chaînes encodées en PEM via des variables d'environnement, décodées en `bytes` au démarrage du processus par un `BeforeValidator` dans le modèle pydantic `Settings`. Il n'y a pas de chargement paresseux — `settings` est un singleton de niveau module instancié au moment de l'import, de sorte qu'une valeur de clé mal configurée échoue immédiatement avant qu'aucune requête ne soit servie. La propriété `is_node_side_encryption_enabled` vérifie si les deux clés du serveur sont présentes, et `tasks_encryption_enabled` est un alias utilisé dans les réponses d'API.

**Stockage des clés du navigateur.** Les clés du navigateur saisies dans la page Paramètres, ainsi que la passphrase de connexion, sont stockées dans `IndexedDB`, chiffrées avec une clé AES-256-GCM liée à l'appareil et non extractible. Cette clé d'appareil est générée à la première connexion à l'aide de `crypto.subtle.generateKey` avec `extractable: false` et ne peut jamais être exportée ni lue sous forme d'octets bruts — pas même à partir d'un dump du système de fichiers du fichier de base de données. Elle est liée à l'origine, elle ne peut donc pas être utilisée depuis un autre domaine ou profil de navigateur. Ni la passphrase ni les clés de l'utilisateur ne sont jamais stockées dans `localStorage` ou envoyées au serveur.

**Génération des clés.** Générez les paires de clés du serveur avec openssl :

```bash
# Server RSA-4096 keypair (private key → TASKS_SERVER_RSA_PRIVATE_KEY env var)
openssl genrsa -out server_rsa_private.pem 4096

# Server ECDSA-P256 keypair (private key → TASKS_SERVER_ECDSA_PRIVATE_KEY env var)
openssl ecparam -genkey -name prime256v1 -noout -out server_ecdsa_ec.pem
openssl pkcs8 -topk8 -nocrypt -in server_ecdsa_ec.pem -out server_ecdsa_private.pem
```

Les clés publiques du serveur ne sont jamais distribuées manuellement — le navigateur les récupère via `GET /tasks/server-public-keys` à l'exécution.

Les paires de clés de l'utilisateur sont générées par le navigateur à la première utilisation et stockées localement dans la page Paramètres. Le navigateur dérive les clés publiques correspondantes à partir des clés privées stockées à l'aide de la Web Crypto API et les intègre dans chaque tâche au moment de la soumission. Aucune configuration de clé publique d'utilisateur n'est requise sur le serveur.

Le chiffrement est facultatif. Si les clés du serveur sont absentes de l'environnement, le chemin correspondant est ignoré et les champs restent en clair.

## Sécurité des wallets

Le node prend en charge plusieurs wallets — chacun identifié par une adresse EVM — afin que différents utilisateurs puissent partager une seule instance de node sans accéder aux tâches ou aux identifiants des autres. La sécurité des wallets repose sur deux couches distinctes que l'on confond souvent : la passphrase, qui sert à l'authentification, et l'enveloppe au repos, qui sert à la protection du stockage.

**Rôle de la passphrase.** La passphrase est un identifiant d'authentification par wallet, et non une clé de chiffrement. Lorsqu'un wallet est enregistré, la passphrase est hachée avec PBKDF2-HMAC-SHA256 à 600 000 itérations et le hash est stocké aux côtés du wallet — la passphrase en clair n'est jamais écrite nulle part. À la connexion, la passphrase entrante est hachée et comparée au condensé stocké à l'aide d'une comparaison à temps constant pour empêcher les attaques temporelles. Cette conception maintient le contrôle d'accès multi-locataire indépendant du chiffrement : le node peut valider qu'un utilisateur est bien celui qu'il prétend être sans avoir besoin de la passphrase à aucune autre fin.

**Stockage des clés privées.** Les clés privées des wallets sont stockées en clair dans le JSON de la liste des wallets plutôt que chiffrées avec la passphrase. Il s'agit d'un compromis intentionnel qui permet le déverrouillage automatique du bot : au démarrage du processus du node, le bot administrateur a besoin de son wallet immédiatement disponible sans attendre qu'un humain saisisse une passphrase. Stocker la clé chiffrée avec la passphrase de l'utilisateur casserait le démarrage sans surveillance. La protection des clés privées au repos provient donc de l'enveloppe de stockage, et non de la passphrase. Lorsque `OCTOBOT_WALLET_AES_KEY` est définie, l'ensemble de la liste des wallets est enveloppé dans AES-256-GCM avant l'écriture sur disque — tout attaquant qui lit le fichier sans la clé de niveau environnement ne voit que du texte chiffré. Sans cette variable d'environnement, la liste des wallets est un JSON en clair, protégé uniquement par les permissions du système de fichiers. Pour les déploiements en production, définir `OCTOBOT_WALLET_AES_KEY` et restreindre l'accès en lecture au fichier de configuration sont les défenses principales.

**Stockage des clés du navigateur par wallet.** Les clés de chiffrement côté navigateur (clés privées RSA et ECDSA) que les utilisateurs configurent dans la page Paramètres sont stockées dans IndexedDB, chiffrées avec une clé dérivée de la passphrase et de l'adresse du wallet de l'utilisateur à l'aide de PBKDF2. La dérivation utilise l'adresse comme sel déterministe, de sorte que chaque adresse de wallet produit une clé de chiffrement différente. Cela a deux conséquences pratiques : premièrement, deux utilisateurs partageant un navigateur ne peuvent pas lire les clés de l'autre, même s'ils peuvent inspecter les enregistrements bruts d'IndexedDB ; deuxièmement, lorsqu'un utilisateur se déconnecte et que la passphrase est effacée de la mémoire, les clés client deviennent inaccessibles — elles sont toujours physiquement présentes dans la base de données mais ne peuvent pas être déchiffrées sans la passphrase. Les sessions sur de nouveaux appareils ou navigateurs démarrent sans clés client et doivent les ressaisir dans les Paramètres.

**Frontière de sécurité.** Un attaquant disposant d'un accès en lecture au disque du node (mais pas à son environnement d'exécution) peut atteindre le fichier de la liste des wallets. Si `OCTOBOT_WALLET_AES_KEY` est absente, il peut extraire directement les clés privées. Si la variable d'environnement est définie, il lui faut à la fois le fichier et la clé. Dans tous les cas, un attaquant disposant à la fois de la liste des wallets et du hash de la passphrase ne gagne rien de plus — le hash de la passphrase ne peut pas être utilisé pour dériver la clé privée, car la clé privée n'a jamais été chiffrée avec la passphrase. Pour les clés du navigateur, un attaquant capable de faire un dump du store IndexedDB (par exemple à la suite d'une compromission d'une machine locale) a tout de même besoin de la passphrase du wallet concerné pour les déchiffrer.

## Import de templates

À la fois le flux d'import CSV et la page d'export des résultats prennent en charge des templates définis par l'utilisateur, chargés depuis des fichiers JSON. Cela permet aux équipes de partager des configurations réutilisables sans toucher au code de l'application.

**Les templates d'import** (utilisés lors de l'import CSV de tâches) composent plusieurs templates d'action de base en un seul template combiné, en les listant comme étapes ordonnées. Chaque étape peut pré-remplir des valeurs de paramètres en tant que valeurs par défaut et marquer des paramètres comme masqués afin qu'ils n'apparaissent pas dans le formulaire. L'interface d'import valide le JSON avec un schéma Zod, vérifie que chaque template de base référencé existe, et rejette tout paramètre requis masqué dépourvu de valeur par défaut — empêchant le formulaire de bloquer silencieusement la soumission. Les templates qui passent la validation sont enregistrés dans `localStorage` et apparaissent immédiatement aux côtés des templates intégrés dans le menu déroulant des actions.

**Les templates d'export** (utilisés sur la page d'export des résultats) définissent des correspondances de colonnes à plat : chaque colonne spécifie un libellé, un chemin JSON dans l'objet de résultat de la tâche, et un formateur optionnel (`text`, `number`, `date` ou `json`). Les chemins JSON commençant et se terminant par un double underscore (par exemple `__task_name__`) se résolvent par rapport aux métadonnées de niveau tâche plutôt qu'au payload de résultat. Comme les templates d'import, les templates d'export sont validés par Zod à l'ingestion, stockés dans `localStorage`, et apparaissent dans le menu déroulant des templates sans rechargement de la page.

Les deux systèmes utilisent le même pattern CRUD adossé à localStorage — chargement, upsert par ID, suppression — et ignorent silencieusement les entrées mal formées au chargement, de sorte qu'un template corrompu ne casse pas l'ensemble de la liste. Les identifiants des templates intégrés sont réservés ; tenter d'importer un template utilisateur ayant le même ID qu'un template intégré lève une erreur.

Des fichiers d'exemple pour les deux systèmes sont livrés avec l'application :
- Exemples de méta-templates d'import : `public/meta-template-examples/`
- Exemples de templates d'export : `public/export-template-examples/`

Le format JSON des templates d'export :

```json
{
  "id": "my_export",
  "label": "My Export",
  "description": "Custom export columns",
  "columns": [
    { "key": "name", "label": "Name", "jsonPath": "__task_name__", "formatter": "text" },
    { "key": "amount", "label": "Amount", "jsonPath": "amount", "formatter": "number" },
    { "key": "fee", "label": "Fee", "jsonPath": "fee.cost", "formatter": "number" }
  ]
}
```
