
Twitter interface
=================

OctoBot uses the Twitter interface for the following purposes:


* Publishing market evaluations and current orders with their status
* Monitoring Twitter accounts given in **TwitterNewsEvaluator.json** configuration and enabling the social evaluator **TwitterNewsEvaluator**

Twitter service configuration
-----------------------------

Add in **user/config.json** in the services key :

.. code-block:: json

   "twitter": {
          "api-key": "YOUR_TWITTER_API_KEY",
          "api-secret": "YOUR_TWITTER_API_SECRET",
          "access-token": "YOUR_TWITTER_ACCESS_TOKEN",
          "access-token-secret": "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
      }

**Exemple:**

.. code-block:: json

   "services": {
      "a service": {

      },
      "twitter": {
          "api-key": "YOUR_TWITTER_API_KEY",
          "api-secret": "YOUR_TWITTER_API_SECRET",
          "access-token": "YOUR_TWITTER_ACCESS_TOKEN",
          "access-token-secret": "YOUR_TWITTER_ACCESS_TOKEN_SECRET"
      },
      "another service": {

      }
   }

All those information can be found after creating a Twitter App.


* Login on your Twitter account if you are not already
* `Generate a Twitter App to your Twitter account if you don't already have one <https://apps.twitter.com/>`_
* In this app page, go to the **Keys and Access Tokens** tab
* Find **api-key** and **api-secret** and copy them in **Consumer Key** and **Consumer Secret**
* Create a new **access-token** if you don't have one already
* Find **access-token** and **access-token-secret** and copy them in **Access Token** and **Access Token Secret**
