Reddit interface
================

OctoBot uses the Reddit interface to monitor reddit posts from subreddits given in **RedditForumEvaluator.json**. This interface enables the social evaluator **RedditForumEvaluator**

Reddit service configuration
----------------------------

Add in **user/config.json** in the services key :

.. code-block:: json

   "reddit": {
          "client-id": "YOUR_CLIENT_ID",
          "client-secret": "YOUR_CLIENT_SECRET",
          "username": "YOUR_REDDIT_USERNAME",
          "password": "YOUR_REDDIT_PASSWORD"
      }

**Exemple:**

.. code-block:: json

   "services": {
      "a service": {

      },
      "reddit": {
          "client-id": "YOUR_CLIENT_ID",
          "client-secret": "YOUR_CLIENT_SECRET",
          "username": "YOUR_REDDIT_USERNAME",
          "password": "YOUR_REDDIT_PASSWORD"
      },
      "another service": {

      }
   }

All those information can be found after creating a Reddit App.


* Login on your Reddit account if you are not already
* `Generate a Reddit script App to your Reddit account if you don't already have one <https://www.reddit.com/prefs/apps/>`_
* **client-id** is the 14 characters identifier under the App's name
* **client-secret** is the **secret** identifier of the App
* **username** and **password** are your usual Reddit username and password
