#  Drakkar-Software OctoBot-Services
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

# Config
CONFIG_CATEGORY_SERVICES = "services"
CONFIG_SERVICE_INSTANCE = "service_instance"

# Interfaces
CONFIG_INTERFACES = "interfaces"
CONFIG_INTERFACES_WEB = "web"
CONFIG_INTERFACES_NODE_WEB = "node_web"
CONFIG_INTERFACES_TELEGRAM = "telegram"

# Service feeds
FEED_METADATA = "metadata"

# Telegram
CONFIG_TELEGRAM = "telegram"
CONFIG_TOKEN = "token"
CONFIG_TELEGRAM_CHANNEL = "telegram-channels"
MESSAGE_PARSE_MODE = 'parse_mode'
CONFIG_TELEGRAM_ALL_CHANNEL = "*"
CONFIG_GROUP_MESSAGE = "group-message"
CONFIG_GROUP_MESSAGE_DESCRIPTION = "group-message-description"
CONFIG_USERNAMES_WHITELIST = "usernames-whitelist"
CONFIG_CHAT_ID = "chat-id"

CONFIG_TELEGRAM_API = "telegram-api"
CONFIG_API = "telegram-api"
CONFIG_API_HASH = "telegram-api-hash"
CONFIG_TELEGRAM_PHONE = "telegram-phone"
CONFIG_TELEGRAM_PASSWORD = "telegram-password"
CONFIG_MESSAGE_CONTENT = "message-content"
CONFIG_MESSAGE_SENDER = "message-sender"
CONFIG_IS_GROUP_MESSAGE = "is-group-message"
CONFIG_IS_CHANNEL_MESSAGE = "is-channel-message"
CONFIG_IS_PRIVATE_MESSAGE = "is-private-message"
CONFIG_MEDIA_PATH = "media-path"

# Web
CONFIG_WEB = "web"
CONFIG_WEB_IP = "ip"
CONFIG_WEB_PORT = "port"
CONFIG_WEB_REQUIRES_PASSWORD = "require-password"
CONFIG_WEB_PASSWORD = "password"
CONFIG_AUTO_OPEN_IN_WEB_BROWSER = "auto-open-in-web-browser"
ENV_WEB_PORT = "WEB_PORT"
ENV_WEB_ADDRESS = "WEB_ADDRESS"
ENV_CORS_ALLOWED_ORIGINS = "CORS_ALLOWED_ORIGINS"
ENV_AUTO_OPEN_IN_WEB_BROWSER = "AUTO_OPEN_IN_WEB_BROWSER"
DEFAULT_SERVER_IP = '0.0.0.0'
DEFAULT_SERVER_PORT = 5001

# Node web (OctoBot Node interface)
CONFIG_NODE_WEB = "node_web"
CONFIG_NODE_WEB_IP = "ip"
CONFIG_NODE_WEB_PORT = "port"
ENV_NODE_WEB_PORT = "NODE_WEB_PORT"
ENV_NODE_WEB_ADDRESS = "NODE_WEB_ADDRESS"
DEFAULT_NODE_WEB_IP = DEFAULT_SERVER_IP
DEFAULT_NODE_WEB_PORT = 8000

# Node API (OctoBot Node interface auth + API URL)
ADMIN_USERNAME = "admin-username"
ADMIN_PASSWORD = "admin-password"
ENV_ADMIN_USERNAME = "ENV_ADMIN_USERNAME"
ENV_ADMIN_PASSWORD = "ENV_ADMIN_PASSWORD"
NODE_API_URL = "node-api-url"
NODE_SQLITE_FILE = "node-sqlite-file"
NODE_REDIS_URL = "node-redis-url"
ENV_NODE_SQLITE_FILE = "ENV_NODE_SQLITE_FILE"
ENV_NODE_REDIS_URL = "ENV_NODE_REDIS_URL"

# Webhook
CONFIG_WEBHOOK = "webhook"
CONFIG_ENABLE_NGROK = "enable-ngrok"
CONFIG_ENABLE_OCTOBOT_WEBHOOK = "enable-octobot-webhook"
CONFIG_NGROK_TOKEN = "ngrok-token"
CONFIG_NGROK_DOMAIN = "ngrok-domain"
CONFIG_WEBHOOK_SERVER_IP = "webhook-bind-ip"
CONFIG_WEBHOOK_SERVER_PORT = "webhook-bind-port"
ENV_WEBHOOK_PORT = "WEBHOOK_PORT"
ENV_WEBHOOK_ADDRESS = "WEBHOOK_ADDRESS"
DEFAULT_WEBHOOK_SERVER_IP = '127.0.0.1'
DEFAULT_WEBHOOK_SERVER_PORT = 9000
TRADINGVIEW_WEBHOOK_SERVICE_NAME = "trading_view"

# GPT
CONFIG_GPT = "GPT"
CONFIG_OPENAI_SECRET_KEY = "openai-secret-key"
CONFIG_LLM_CUSTOM_BASE_URL = "llm-custom-base-url"
CONFIG_LLM_MODEL = "llm-model"
CONFIG_LLM_MODEL_FAST = "llm-model-fast"
CONFIG_LLM_MODEL_REASONING = "llm-model-reasoning"
CONFIG_LLM_DAILY_TOKENS_LIMIT = "llm-daily-tokens-limit"
CONFIG_LLM_SHOW_REASONING = "llm-show-reasoning"
CONFIG_LLM_REASONING_EFFORT = "llm-reasoning-effort"
CONFIG_LLM_MCP_SERVERS = "llm-mcp-servers"
CONFIG_LLM_AUTO_INJECT_MCP_TOOLS = "llm-auto-inject-mcp-tools"
ENV_OPENAI_SECRET_KEY = "OPENAI_SECRET_KEY"
ENV_GPT_MODEL = "GPT_MODEL"
ENV_GPT_DAILY_TOKENS_LIMIT = "GPT_DAILY_TOKEN_LIMIT"

# MCP
CONFIG_MCP = "mcp"
CONFIG_MCP_IP = "ip"
CONFIG_MCP_PORT = "port"
ENV_MCP_PORT = "MCP_PORT"
ENV_MCP_ADDRESS = "MCP_ADDRESS"
DEFAULT_MCP_IP = '127.0.0.1'
DEFAULT_MCP_PORT = 3001

# Google
CONFIG_GOOGLE = "google"
CONFIG_TREND_TOPICS = "trends"
CONFIG_TREND = "trend"
CONFIG_TREND_DESCRIPTION = "trend_description"
CONFIG_TREND_HISTORY_TIME = "relevant_history_months"

# TradingView
CONFIG_TRADING_VIEW = "trading-view"
CONFIG_REQUIRE_TRADING_VIEW_TOKEN = "require-token"
CONFIG_TRADING_VIEW_TOKEN = "token"
CONFIG_TRADING_VIEW_USE_EMAIL_ALERTS = "use-email-alerts"
TRADING_VIEW_USING_EMAIL_INSTEAD_OF_WEBHOOK = "Using email alerts instead of webhook"

# Twitter
CONFIG_TWITTERS_ACCOUNTS = "accounts"
CONFIG_TWITTERS_HASHTAGS = "hashtags"
CONFIG_TWITTER = "twitter"
CONFIG_TWITTER_API_INSTANCE = "twitter_api_instance"
CONFIG_TWEET = "tweet"
CONFIG_TWEET_DESCRIPTION = "tweet_description"
CONFIG_TW_API_KEY = "api-key"
CONFIG_TW_API_SECRET = "api-secret"
CONFIG_TW_ACCESS_TOKEN = "access-token"
CONFIG_TW_ACCESS_TOKEN_SECRET = "access-token-secret"

# Bird (Bird CLI - read-only Twitter/X)
CONFIG_BIRD = "bird"
CONFIG_BIRD_CLI_PATH = "cli-path"
CONFIG_BIRD_ACCOUNT = "account"

# Tavily (Tavily API - web search)
CONFIG_TAVILY = "tavily"
CONFIG_TAVILY_API_KEY = "api-key"
CONFIG_TAVILY_PROJECT_ID = "project-id"

# SearXNG (self-hosted web search)
CONFIG_SEARXNG = "searxng"
CONFIG_SEARXNG_URL = "url"
CONFIG_SEARXNG_PORT = "port"
CONFIG_SEARXNG_CATEGORIES = "categories"
CONFIG_SEARXNG_LANGUAGE = "language"
CONFIG_SEARXNG_TIME_RANGE = "time_range"
CONFIG_SEARXNG_SAFE_SEARCH = "safe_search"
CONFIG_SEARXNG_ENGINES = "engines"

# Reddit
CONFIG_REDDIT = "reddit"
CONFIG_REDDIT_SUBREDDITS = "subreddits"
CONFIG_REDDIT_ENTRY = "entry"
CONFIG_REDDIT_ENTRY_WEIGHT = "entry_weight"
CONFIG_REDDIT_CLIENT_ID = "client-id"
CONFIG_REDDIT_CLIENT_SECRET = "client-secret"
CONFIG_REDDIT_PASSWORD = "password"
CONFIG_REDDIT_USERNAME = "username"

# Coindesk
CONFIG_COINDESK = "coindesk"
CONFIG_COINDESK_API_KEY = "api-key"
CONFIG_COINDESK_LANGUAGE = "lang"
CONFIG_COINDESK_REFRESH_TIME_FRAME = "refresh_time_frame"
CONFIG_COINDESK_TOPICS = "topics"
COINDESK_TOPIC_MARKETCAP = "topic_marketcap"
COINDESK_TOPIC_NEWS = "topic_news"
COINDESK_DATA_KEY = "data"

# Lunarcrush
CONFIG_LUNARCRUSH = "lunarcrush"
CONFIG_LUNARCRUSH_API_KEY = "api-key"
CONFIG_LUNARCRUSH_REFRESH_TIME_FRAME = "refresh_time_frame"
CONFIG_LUNARCRUSH_COINS = "coins"
LUNARCRUSH_COIN_METRICS = "coin_metrics"
LUNARCRUSH_DATA_KEY = "data"

# Alternative.me
CONFIG_ALTERNATIVE_ME = "alternative_me"
CONFIG_ALTERNATIVE_ME_TOPICS = "topics"
CONFIG_ALTERNATIVE_ME_REFRESH_TIME_FRAME = "refresh_time_frame"
ALTERNATIVE_ME_TOPIC_FEAR_AND_GREED = "topic_fear_and_greed"
ALTERNATIVE_ME_DATA_KEY = "data"

# Coingecko
CONFIG_COINGECKO = "coingecko"
CONFIG_COINGECKO_API_KEY = "api-key"
CONFIG_COINGECKO_TOPICS = "topics"
CONFIG_COINGECKO_REFRESH_TIME_FRAME = "refresh_time_frame"
CONFIG_COINGECKO_COINS = "coins"
COINGECKO_TOPIC_MARKETS = "topic_markets"
COINGECKO_TOPIC_TRENDING = "topic_trending"
COINGECKO_TOPIC_GLOBAL = "topic_global"
COINGECKO_DATA_KEY = "data"

# Exchange
CONFIG_EXCHANGE = "exchange"
CONFIG_EXCHANGE_PROFILES = "profiles"
CONFIG_EXCHANGE_PROFILE_ID = "id"

# Notifications
CONFIG_CATEGORY_NOTIFICATION = "notification"
CONFIG_NOTIFICATION_TYPE = "notification-type"

# Interfaces
PAID_FEES_STR = "Paid fees"

# external resources
EXTERNAL_RESOURCE_CURRENT_USER_FORM = "current-user-feedback-form"
EXTERNAL_RESOURCE_PUBLIC_ANNOUNCEMENTS = "public-announcements"
