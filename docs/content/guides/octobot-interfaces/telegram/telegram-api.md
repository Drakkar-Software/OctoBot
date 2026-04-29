---
title: "Telegram API"
description: "Learn how to configure your OctoBot to trade based on signals from Telegram channels."
sidebar_position: 1
---



# Telegram API

Telegram API allows your OctoBot to listen to telegram **public groups**.

:::info
  The Telegram API configuration is not necessary if your goal is to command your OctoBot from Telegram or to have your OctoBot listen to a private group. In those cases, the [initial Telegram configuration](.) is enough.
:::


## Create your App

Before working with Telegram’s API, you need to get your own API ID and hash:

In order to obtain an API id and develop your own application using the Telegram API you need to do the following:

- Sign up for Telegram using any application.
- Log in to your Telegram core: https://my.telegram.org.
- Go to 'API development tools' and fill out the form.
- You will get basic addresses as well as the **api_id** and **api_hash** parameters required for user authorization.


## Configuration


Add in **user/config.json** in the services key :

``` json
"telegram-api": {
    "telegram-api": "YOUR_API_ID",
    "telegram-api-hash": "YOUR_API_HASH",
    "telegram-phone": "YOUR_TELEGRAM_ACCOUNT_PHONE_NUMBER"
}
```

### Secure code

At the first OctoBot start with a new `telegram-api` configuration a 2-factor authentication code will be sent to your account.
Just enter it the code in your OctoBot console and press enter.

> If you are asked a password and Telegram didn't send it to you, try to provide the mobile phone number without "+".
