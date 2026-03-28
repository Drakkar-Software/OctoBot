---
title: "Web interface"
description: "Learn how to configure your OctoBot web interface. Secure it with a password authentication, set it up to have multiple OctoBots on the same computer."
sidebar_position: 1
---



# Web interface

![home](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/home.jpg)

OctoBot comes with a web interface allowing you to:

- Follow OctoBot's status and moves
- Interact with OctoBot
- Configure OctoBot and the [Trading Modes](/guides/octobot-trading-modes/trading-modes) to use
- Use [Backtesting](/guides/octobot-usage/backtesting) to optimize your strategies

## Configuration

In the Accounts tab of the web interface, add the `Web` interface if missing.

![web config](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/web_config.png)

- **port** is the port you want the web interface to be accessible from. Changing it allows you to [have multiple OctoBots running on the same computer](../octobot-usage/having-multiple-octobots-on-one-computer).
- **auto open in web browser** is whether starting your OctoBot should open a new tab on your browser to display the web interface
- **requires password** is whether the web interface of your OctoBot should be protected by a password

## Protect your web interface

### Using an authentication password

You can set a password to protect your web interface. This way you can secure the access to your OctoBot when hosting it on a cloud or just add a security layer to your setup.

**By default no password is required.**

You can activate the password authentication from the web interface configuration, it is also where you can set and change your password.

Any IP will be automatically **blocked after 10 authentication failures in a row**. IPs will remain blocked until your OctoBot restarts. If you accidentally block your IP, you can just restart your OctoBot.

### How to set it up ?

- Go to "Accounts" page
- Select "Interfaces" on the left menu
- Click on "**\*\*\*\***" next to "Password: "
- Override the "\*\*\*\*" with your password
- Click on validate
- Click on "SAVE AND RESTART" red button on the left menu

### You forgot your password

If you forgot your password, go to your **user/config.json** file and change:

```json
"require-password": true,
```

into:

```json
"require-password": false,
```

Then restart your OctoBot. This way you will be able to access your OctoBot without a password and then change it.

### About the web interface authentication

- OctoBot's web interface authentication works on the assumption that you are the only person being able to access your OctoBot's file system and the associated processes. This authentication can be deactivated by anyone being able to edit your **user/config.json** and restart your OctoBot process.
- Only a SHA256 hash of your password will be stored in you **user/config.json** file. This is making it impossible to go back to the original password you entered.

### Blocking requests from other websites (CSRF)

You can set the `CORS_ALLOWED_ORIGINS` environment variable before starting your OctoBot, this way only requests from the specified origin(s) will be answered to.

Examples:

- `CORS_ALLOWED_ORIGINS=https://mybot.com`
- `CORS_ALLOWED_ORIGINS=http://localhost:5001`
- `CORS_ALLOWED_ORIGINS=https://mybot.com,https://myotherwebsite.com`

Requests from other origins will be refused with a 400 error and the web interface will behave as if OctoBot was constantly disconnected.

By default, no request filter is set (equivalent to CORS_ALLOWED_ORIGINS=\*) which might make your bot vulnerable to <a href="https://owasp.org/www-community/attacks/csrf" rel="nofollow">Cross Site Request Forgery attacks</a>.

### user/config.json configuration

Add in **user/config.json** in the services key :

```json
"web": {
    "auto-open-in-web-browser": false,
    "ip": "0.0.0.0",
    "password": "",
    "port": 5001,
    "require-password": false
}
```

You can also change the IP your web interface is binding to from **user/config.json**.

**Example:**

```json
"services": {
   "a service": {

   },
   "web": {
        "auto-open-in-web-browser": false,
        "ip": "0.0.0.0",
        "password": "",
        "port": 5001,
        "require-password": false
   },
   "another service": {

   }
}
```
