---
title: "Reddit"
description: "Learn how to configure your OctoBot to trade using Reddit and watch subreddits to trade according to the Reddit posts."
sidebar_position: 5
---



# Trading based on Reddit posts

<div style="text-align: center">
  ![reddit trading automation illustrated by reddit
  logo](/images/guides/interfaces/reddit-connection-to-octobot-illustrated-by-reddit-logo.png)
</div>

OctoBot can connect to <a href="https://www.reddit.com" rel="nofollow">Reddit</a> to monitor Reddit posts from subreddits.

When the **RedditForumEvaluator** is enabled, OctoBot will the use <a href="https://github.com/cjhutto/vaderSentiment" rel="nofollow">VADER Sentiment Analysis's AI</a> to analyse the sentiment of each post and make a summary of each coin to be used by the [Daily Trading Mode](/guides/octobot-trading-modes/daily-trading-mode).

## RedditForumEvaluator configuration

In the Accounts tab of the web interface, add the `Reddit` interface if missing.

![RedditForumEvaluator configuration to select subreddits to follow](/images/guides/interfaces/RedditForumEvaluator-configuration-to-select-subreddits-to-follow.png)

Configure the **RedditForumEvaluator** to specify the subreddits to follow for each traded Cryptocurrency.

## Reddit connection configuration

To connect to Reddit, OctoBot needs a Reddit script app, which you can create from your Reddit account, or a new account dedicated to OctoBot.

<div style="text-align: center">
   ![reddit octobot config](/images/guides/interfaces/reddit-octobot-config.png)
</div>

1. Login on your Reddit account if you already have one
2. Go to your account's <a href="https://www.reddit.com/prefs/apps/" rel="nofollow">Applications preferences</a>.
3. Create a new `script` app
   <div style="text-align: center">
      ![reddit create app](/images/guides/interfaces/reddit-create-app.png)
   </div>
   - `Name` and `description` can be set as you wish
   - Leave `About URL` empty
   - `Redirect URI` won't be used, enter `https://www.reddit.com/` (or any other valid url)
   - Create your app 
3. **Client-Id** is the list of characters under your App name, next to its icon
4. **Client-Secret** is the **secret** identifier of the App
<div style="text-align: center">
   ![reddit created app](/images/guides/interfaces/reddit-created-app.png)
</div>

Copy and paste your new Reddit app details into your OctoBot configuration.
<div style="text-align: center">
   ![reddit octobot config](/images/guides/interfaces/reddit-octobot-config.png)
</div>


### Configuration from user/config.json

Add in **user/config.json** in the services key :

```json
"reddit": {
       "client-id": "YOUR_CLIENT_ID",
       "client-secret": "YOUR_CLIENT_SECRET"
   }
```

**Exemple:**

```json
"services": {
   "a service": {

   },
   "reddit": {
       "client-id": "YOUR_CLIENT_ID",
       "client-secret": "YOUR_CLIENT_SECRET"
   },
   "another service": {

   }
}
```
