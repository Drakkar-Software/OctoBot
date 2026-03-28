---
title: "Installation en cloud"
description: "Installez votre OctoBot dans le cloud avec DigitalOcean en quelques minutes et  bénéficiez de vos stratégies OctoBot 24h/24"
sidebar_position: 2
---



# Installer OctoBot dans le cloud avec DigitalOcean

## Créer un compte DigitalOcean

- Créez un compte sur DigitalOcean en suivant ce lien : <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">DigitalOcean</a> (ou connectez-vous si vous en avez déjà un).

- Validez votre compte en ajoutant un moyen de paiement.

## Démarrer l'application OctoBot

- Ouvrez la page de l'application <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">OctoBot</a> sur la marketplace de Digital Ocean.

- Cliquez sur "Créer un Droplet OctoBot".

![DigitalOcean Create Droplet Button](/images/guides/installation/digitalocean/digital-ocean-octobot-app-page.png)

- Choisissez une région proche de vous.

![Choix de région du Droplet de DigitalOcean](/images/guides/installation/digitalocean/choose-droplet-location.png)

- Laissez l'image de l'application OctoBot sélectionnée.

![DigitalOcean Droplet choose region](/images/guides/installation/digitalocean/digital-ocean-octobot-image.png)

- Sélectionnez la puissance du serveur que vous voulez. Le minimum requis est l'offre à $6 / mois.

![DigitalOcean Droplet choose pricing](/images/guides/installation/digitalocean/digital-ocean-droplet-pricing.png)

- Entrez un mot de passe sécurisé ou une clé SSH.

![DigitalOcean Droplet choose pricing](/images/guides/installation/digitalocean/digital-ocean-droplet-access.png)

- Cliquez en bas sur "Create droplet".

- Attendez que le Droplet démarre.

![Attente du démarrage du Droplet de DigitalOcean](/images/guides/installation/digitalocean/wait-for-droplet-start.png)

## Accéder à OctoBot

- Sur la page du Droplet DigitalOcean, récupérez l'IP du Droplet. Par exemple, dans cet exemple, c'est l'IP `143.198.96.188`.

![Adresse IP du Droplet DigitalOcean](/images/guides/installation/digitalocean/get-droplet-ip.png)

- Copiez cette adresse.
- Dans votre navigateur, ouvrez un nouvel onglet et tapez http://$DROPLET_IP. Dans cet exemple il faudrait taper `http://143.198.96.188`.

<div style={{textAlign: "center"}}>
  ![ouvrir l'interface web d'OctoBot avec l'IP du
  droplet](/images/guides/installation/digitalocean/open-octobot-with-droplet-ip.png)
</div>

- Si votre navigateur indique que la connexion n'est pas sécurisée (ce qui est normal car elle n'est pas en HTTPS), acceptez en cliquant sur "continuer vers le site".

- Après quelques secondes, l'interface web de votre OctoBot devrait apparaître.

:::warning
  Attention : Comme n'importe qui connaissant l'IP de votre OctoBot peut ouvrir
  cette interface, il est fortement recommandé d'ajouter un [mot de passe de
  protection](/fr/guides/octobot-interfaces/web#prot%C3%A9ger-votre-interface-web).
:::
