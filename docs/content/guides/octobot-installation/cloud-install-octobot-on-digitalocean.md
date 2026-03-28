---
title: "In the cloud"
description: "Install your OctoBot in the cloud with DigitalOcean in a few minutes and have your OctoBot trading using your strategies 24/7"
sidebar_position: 2
---



# Install OctoBot in the cloud with DigitalOcean

## Create a DigitalOcean account

- Create an account on DigitalOcean by following this link: <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">DigitalOcean</a> (or log in if you already have one).

- Validate your account by adding a payment method.

## Start the OctoBot application

- Open the <a href="https://digitalocean.pxf.io/octobot-app" rel="nofollow">OctoBot App page</a> on Digital Ocean marketplace.

- Click on "Create OctoBot droplet".

![DigitalOcean Create Droplet Button](/images/guides/installation/digitalocean/digital-ocean-octobot-app-page.png)

- Choose a region close to you.

![DigitalOcean Droplet choose region](/images/guides/installation/digitalocean/choose-droplet-location.png)

- Let the OctoBot application image selected

![DigitalOcean Droplet choose region](/images/guides/installation/digitalocean/digital-ocean-octobot-image.png)

- Select the desired server power. The minimal requirement is the $6/month option.

![DigitalOcean Droplet choose pricing](/images/guides/installation/digitalocean/digital-ocean-droplet-pricing.png)

- Enter a secure password or a ssh key.

![DigitalOcean Droplet choose pricing](/images/guides/installation/digitalocean/digital-ocean-droplet-access.png)

- Click at the bottom on "Create droplet".

- Wait for the Droplet to start.

![DigitalOcean Droplet wait for boot complete](/images/guides/installation/digitalocean/wait-for-droplet-start.png)

## Access OctoBot

- On the DigitalOcean Droplet page, get the Droplet's IP. For example, in this example, it's IP `143.198.96.188`.

![DigitalOcean droplet IP address](/images/guides/installation/digitalocean/get-droplet-ip.png)

- Copy this address.

- In your browser, open a new tab and type http://$DROPLET_IP. In this example, you would type `http://143.198.96.188`.

<div style="text-align: center">

![open OctoBot web interface with droplet IP](/images/guides/installation/digitalocean/open-octobot-with-droplet-ip.png)

</div>

- If your browser indicates that the connection is not secure (which is normal because it is not HTTPS), accept by clicking "continue to the site".

- After a few seconds, the web interface of your OctoBot should appear.

:::warning
  Attention: Since anyone knowing the IP of your OctoBot can open this
  interface, it is strongly recommended to add a [password
  protection](/en/guides/octobot-interfaces/web#protect-your-web-interface).
:::
