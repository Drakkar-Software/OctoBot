
Using a webhook with OctoBot
============================

There are many ways to wake your OctoBot up and make it do something, one of them is using a webhook. With a webhook, you can automatically send messages to your OctoBot from any website supporting this system. https://www.tradingview.com is one of them.

In order to be able to receive the webhook's message, OctoBot has to expose an API to the web, for this it uses https://ngrok.com/ that acts as a secure intermediary between the internet and your OctoBot.

Setting up your OctoBot's webhook
---------------------------------


#. In OctoBot configuration, add the webhook service.
#. To get your OctoBot's webhook address (the url other websites will use to send messages to your OctoBot), create an account on https://ngrok.com/ and enter your ngrok token into your webhook service configuration.
#. Activate a tentacle using a webhook service (like the trading view signals trading mode).
#. Restart your OctoBot.
#. The webhook address will be displayed on your OctoBot configuration and printed in your logs.

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/webhook_config.jpg
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/webhook_config.jpg
      :alt: webhook and tradingview config


   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/webhook_log.jpg
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/webhook_log.jpg
      :alt: webhook log

   ## About ngrok.com
   You can use ngrok with a free account, the only drawback of having a free version is that your webhoob address will change at every OctoBot restart, you will have to update it on your message sender (like https://www.tradingview.com)
