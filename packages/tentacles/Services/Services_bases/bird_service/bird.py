#  Drakkar-Software OctoBot-Tentacles
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
import asyncio
import json
import os
import subprocess
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from urllib.parse import quote

import octobot_services.constants as services_constants
import octobot_services.enums as services_enums
import octobot_services.services as services

from .models import Tweet, Reply, Like, Bookmark, NewsItem


class BirdService(services.AbstractService):
    BIRD_COMMAND_TIMEOUT = 60
    BIRD_HELP_URL = "https://github.com/steipete/bird"

    def __init__(self):
        super().__init__()
        self._cli_path: str = "bird"
        self._account: Optional[str] = None
        self._startup_message: str = ""
        self._startup_healthy: bool = False

    @staticmethod
    def is_bird_available(cli_path: str) -> bool:
        """
        Return True if the bird binary at cli_path is available (found and executable).
        cli_path can be a bare command name (e.g. "bird") or a full path.
        """
        if not cli_path or not cli_path.strip():
            return False
        path = cli_path.strip()
        if os.sep in path or path.startswith("/"):
            return os.path.isfile(path) and os.access(path, os.X_OK)
        return shutil.which(path) is not None

    async def _run_command_async(self, args: List[str], timeout: Optional[int] = BIRD_COMMAND_TIMEOUT) -> str:
        cmd = [self._cli_path] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            self.logger.error(f"Bird CLI command timed out: {' '.join(cmd)}")
            raise
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""
        if proc.returncode != 0:
            self.logger.error(f"Bird CLI command failed: {' '.join(cmd)}: {stderr_text}")
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, stdout_text, stderr_text
            )
        return stdout_text

    def _parse_list_output(
        self,
        output: str,
        item_keys: Tuple[str, ...],
        from_dict: Callable[[Dict[str, Any]], Any],
    ) -> List[Any]:
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [from_dict(item) for item in data]
        items = None
        for key in item_keys:
            if key in data:
                items = data[key]
                break
        if items is None:
            items = []
        if isinstance(items, dict):
            items = [items]
        return [from_dict(item) for item in items] if items else []

    def _parse_tweets_output(self, output: str) -> List[Tweet]:
        return self._parse_list_output(output, ("tweets", "tweet"), Tweet.from_dict)

    def _parse_user_tweets_output(self, output: str) -> List[Tweet]:
        return self._parse_list_output(
            output, ("userTweets", "user_tweets", "tweets", "tweet"), Tweet.from_dict
        )

    def _parse_mentions_output(self, output: str) -> List[Tweet]:
        return self._parse_list_output(output, ("mentions", "tweets", "tweet"), Tweet.from_dict)

    def _parse_single_tweet(self, output: str) -> Optional[Tweet]:
        try:
            data = json.loads(output)
            return Tweet.from_dict(data) if data else None
        except json.JSONDecodeError:
            return None

    def _parse_replies_output(self, output: str) -> List[Reply]:
        return self._parse_list_output(output, ("tweets", "tweet"), Reply.from_dict)

    def _parse_search_replies_output(self, output: str) -> List[Reply]:
        return self._parse_list_output(
            output, ("results", "searchResults", "tweets", "tweet"), Reply.from_dict
        )

    def _parse_list_timeline_output(self, output: str) -> List[Tweet]:
        """Parse list-timeline JSON; bird may use list, listTweets, tweets, or tweet."""
        return self._parse_list_output(
            output, ("list", "listTweets", "tweets", "tweet"), Tweet.from_dict
        )

    def _parse_likes_output(self, output: str) -> List[Like]:
        return self._parse_list_output(output, ("tweets", "tweet"), Like.from_dict)

    def _parse_bookmarks_output(self, output: str) -> List[Bookmark]:
        return self._parse_list_output(output, ("tweets", "tweet"), Bookmark.from_dict)

    def _parse_news_output(self, output: str) -> List[NewsItem]:
        return self._parse_list_output(output, ("news", "items"), NewsItem.from_dict)

    @staticmethod
    def _extract_user_list(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        for key in ("users", "following", "followers", "list", "entries"):
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    return [val]
        result = data.get("result")
        if isinstance(result, dict):
            for key in ("users", "following", "followers", "list", "entries"):
                if key in result:
                    val = result[key]
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        return [val]
        return []

    def get_type(self):
        return services_constants.CONFIG_BIRD

    def get_endpoint(self):
        return self

    @staticmethod
    def is_setup_correctly(config):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in config
            and services_constants.CONFIG_BIRD in config[services_constants.CONFIG_CATEGORY_SERVICES]
            and services_constants.CONFIG_SERVICE_INSTANCE
            in config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_BIRD]
        )

    def has_required_configuration(self):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in self.config
            and services_constants.CONFIG_BIRD in self.config[services_constants.CONFIG_CATEGORY_SERVICES]
        )

    async def prepare(self):
        bird_config = self.config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(
            services_constants.CONFIG_BIRD, {}
        )
        self._cli_path = bird_config.get(services_constants.CONFIG_BIRD_CLI_PATH, "bird") or "bird"
        account = bird_config.get(services_constants.CONFIG_BIRD_ACCOUNT, "")
        self._account = account.strip() or None

        if not self.is_bird_available(self._cli_path):
            self._startup_healthy = False
            self._startup_message = f"Bird CLI not found or not executable: {self._cli_path!r}"
            return

        try:
            try:
                msg = (await self._run_command_async(["whoami"])).strip()
            except Exception:
                msg = (await self._run_command_async(["--version"])).strip()
        except Exception as e:
            self._startup_healthy = False
            self._startup_message = ""
            self.logger.error(f"Bird CLI startup check failed: {e}")
        else:
            self._startup_healthy = bool(msg)
            self._startup_message = (
                f"Bird CLI ready: {msg}" if msg else "Bird CLI check completed."
            )
            if msg and not self._account:
                self._account = msg if msg.startswith("@") else f"@{msg}"

    def get_successful_startup_message(self):
        return self._startup_message, self._startup_healthy

    def get_fields_description(self):
        return {
            services_constants.CONFIG_BIRD_CLI_PATH: "Path to the Bird CLI binary (default: 'bird' from PATH).",
            services_constants.CONFIG_BIRD_ACCOUNT: "Optional Twitter/X handle for user-tweets, about, etc.",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_BIRD_CLI_PATH: "bird",
            services_constants.CONFIG_BIRD_ACCOUNT: "",
        }

    def get_required_config(self):
        return []

    @classmethod
    def get_help_page(cls) -> str:
        return cls.BIRD_HELP_URL

    def get_website_url(self) -> str:
        return self.BIRD_HELP_URL

    def get_read_only_info(self) -> list:
        if not self._account:
            return []
        profile_url = f"https://x.com/{self._account.lstrip('@')}"
        return [
            services.ReadOnlyInfo(
                "Account",
                self._account,
                services_enums.ReadOnlyInfoType.CLICKABLE,
                path=profile_url,
            )
        ]

    @staticmethod
    def build_tweet_url(
        text: str = "",
        *,
        url: Optional[str] = None,
        hashtags: Optional[Union[List[str], str]] = None,
        via: Optional[str] = None,
        related: Optional[Union[List[str], str]] = None,
    ) -> str:
        """
        Build a URL that opens Twitter/X compose form with pre-filled params.
        X Web Intent supports: text, url, hashtags, via, related.
        """
        params: List[str] = []
        if text:
            params.append(f"text={quote(text, safe='')}")
        if url:
            params.append(f"url={quote(url, safe='')}")
        if hashtags is not None:
            tags = ",".join(hashtags) if isinstance(hashtags, list) else hashtags
            if tags:
                params.append(f"hashtags={quote(tags.strip(), safe='')}")
        if via:
            params.append(f"via={quote(via.lstrip('@'), safe='')}")
        if related is not None:
            rel = ",".join(related) if isinstance(related, list) else related
            if rel:
                params.append(f"related={quote(rel, safe='')}")
        base = "https://twitter.com/intent/tweet"
        return f"{base}?{'&'.join(params)}" if params else base

    @staticmethod
    def build_reply_url(
        tweet_id: str,
        text: str = "",
        *,
        url: Optional[str] = None,
        hashtags: Optional[Union[List[str], str]] = None,
        via: Optional[str] = None,
        related: Optional[Union[List[str], str]] = None,
    ) -> str:
        """
        Build a URL that opens Twitter/X reply form for the given tweet.
        Optional params: url, hashtags, via, related.
        """
        tid = str(tweet_id).strip()
        if not tid:
            return BirdService.build_tweet_url(
                text=text, url=url, hashtags=hashtags, via=via, related=related
            )
        params: List[str] = [f"in_reply_to={tid}"]
        if text:
            params.append(f"text={quote(text, safe='')}")
        if url:
            params.append(f"url={quote(url, safe='')}")
        if hashtags is not None:
            tags = ",".join(hashtags) if isinstance(hashtags, list) else hashtags
            if tags:
                params.append(f"hashtags={quote(tags.strip(), safe='')}")
        if via:
            params.append(f"via={quote(via.lstrip('@'), safe='')}")
        if related is not None:
            rel = ",".join(related) if isinstance(related, list) else related
            if rel:
                params.append(f"related={quote(rel, safe='')}")
        return f"https://twitter.com/intent/tweet?{'&'.join(params)}"

    async def whoami(self) -> str:
        try:
            return (await self._run_command_async(["whoami"])).strip()
        except Exception as e:
            self.logger.error(f"Bird whoami failed: {e}")
            return ""

    async def check(self) -> str:
        try:
            return (await self._run_command_async(["check"])).strip()
        except Exception as e:
            self.logger.error(f"Bird check failed: {e}")
            return ""

    async def read_tweet(self, tweet_id_or_url: str) -> Optional[Tweet]:
        try:
            out = await self._run_command_async(["read", tweet_id_or_url, "--json"])
            return self._parse_single_tweet(out)
        except Exception as e:
            self.logger.error(f"Bird read_tweet failed: {e}")
            return None

    async def get_timeline(self, limit: int = 20, following_only: bool = False) -> List[Tweet]:
        try:
            args = ["home", "-n", str(limit), "--json"]
            if following_only:
                args.insert(2, "--following")
            out = await self._run_command_async(args)
            return self._parse_tweets_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_timeline failed: {e}")
            return []

    async def get_thread(self, tweet_id: str, max_pages: Optional[int] = None) -> List[Tweet]:
        try:
            args = ["thread", tweet_id, "--json"]
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            return self._parse_tweets_output(out)
        except Exception as e:
            self.logger.error(f"Bird get_thread failed: {e}")
            return []

    async def get_replies(self, tweet_id: str, limit: int = 20, max_pages: Optional[int] = None) -> List[Reply]:
        try:
            args = ["replies", tweet_id, "--json"]
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            return self._parse_replies_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_replies failed: {e}")
            return []

    async def search_tweets(self, query: str, limit: int = 20) -> List[Tweet]:
        try:
            out = await self._run_command_async(["search", query, "-n", str(limit), "--json"])
            return self._parse_tweets_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird search_tweets failed: {e}")
            return []

    async def get_mentions(self, limit: int = 20, user: Optional[str] = None) -> List[Tweet]:
        try:
            args = ["mentions", "-n", str(limit), "--json"]
            if user:
                args.extend(["--user", user])
            out = await self._run_command_async(args)
            return self._parse_mentions_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_mentions failed: {e}")
            return []

    async def get_user_posts(self, limit: int = 20) -> List[Tweet]:
        handle = self._account or ""
        if not handle:
            self.logger.error("Account not set for get_user_posts")
            return []
        try:
            handle = handle if handle.startswith("@") else f"@{handle}"
            out = await self._run_command_async(["user-tweets", handle, "-n", str(limit), "--json"])
            return self._parse_user_tweets_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_user_posts failed: {e}")
            return []

    async def get_user_replies(self, limit: int = 20) -> List[Reply]:
        handle = self._account or ""
        if not handle:
            self.logger.error("Account not set for get_user_replies")
            return []
        try:
            handle = handle if handle.startswith("@") else f"@{handle}"
            out = await self._run_command_async(["search", f"from:{handle} filter:replies", "-n", str(limit), "--json"])
            return self._parse_search_replies_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_user_replies failed: {e}")
            return []

    async def scroll_user_posts(
        self, cursor: Optional[str] = None, max_pages: int = 1
    ) -> Dict[str, Any]:
        handle = self._account or ""
        if not handle:
            self.logger.error("Account not set for scroll_user_posts")
            return {"tweets": [], "next_cursor": None}
        try:
            handle = handle if handle.startswith("@") else f"@{handle}"
            args = ["user-tweets", handle, "--json", "--max-pages", str(max_pages)]
            if cursor:
                args.extend(["--cursor", cursor])
            out = await self._run_command_async(args)
            data = json.loads(out) if out.strip() else {}
            tweets = self._parse_tweets_output(out)
            next_cursor = data.get("nextCursor") or data.get("next_cursor")
            return {"tweets": tweets, "next_cursor": next_cursor}
        except Exception as e:
            self.logger.error(f"Bird scroll_user_posts failed: {e}")
            return {"tweets": [], "next_cursor": None}

    async def scroll_timeline(self, cursor: Optional[str] = None, max_pages: int = 1) -> Dict[str, Any]:
        try:
            out = await self._run_command_async(["home", "-n", "20", "--json"])
            tweets = self._parse_tweets_output(out)
            return {"tweets": tweets, "next_cursor": None}
        except Exception as e:
            self.logger.error(f"Bird scroll_timeline failed: {e}")
            return {"tweets": [], "next_cursor": None}

    async def scroll_search(
        self, query: str, cursor: Optional[str] = None, max_pages: int = 1
    ) -> Dict[str, Any]:
        try:
            args = ["search", query, "--json", "--max-pages", str(max_pages)]
            if cursor:
                args.extend(["--cursor", cursor])
            else:
                args.append("--all")
            out = await self._run_command_async(args)
            data = json.loads(out) if out.strip() else {}
            tweets = self._parse_tweets_output(out)
            next_cursor = data.get("nextCursor") or data.get("next_cursor")
            return {"tweets": tweets, "next_cursor": next_cursor}
        except Exception as e:
            self.logger.error(f"Bird scroll_search failed: {e}")
            return {"tweets": [], "next_cursor": None}

    async def get_bookmarks(
        self,
        limit: int = 20,
        folder_id: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> List[Bookmark]:
        try:
            args = ["bookmarks", "-n", str(limit), "--json"]
            if folder_id:
                args.extend(["--folder-id", folder_id])
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            return self._parse_bookmarks_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_bookmarks failed: {e}")
            return []

    async def get_likes(self, limit: int = 20, max_pages: Optional[int] = None) -> List[Like]:
        try:
            args = ["likes", "-n", str(limit), "--json"]
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            return self._parse_likes_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_likes failed: {e}")
            return []

    async def get_news(
        self,
        limit: int = 10,
        ai_only: bool = False,
        with_tweets: bool = False,
        tabs: Optional[List[str]] = None,
    ) -> List[NewsItem]:
        try:
            args = ["news", "-n", str(limit), "--json"]
            if ai_only:
                args.append("--ai-only")
            if with_tweets:
                args.append("--with-tweets")
            if tabs:
                for t in tabs:
                    if t in ("for-you", "news-only", "sports", "entertainment", "trending-only"):
                        args.append(f"--{t}")
            out = await self._run_command_async(args)
            return self._parse_news_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_news failed: {e}")
            return []

    async def get_list_timeline(
        self,
        list_id_or_url: str,
        limit: int = 20,
        max_pages: Optional[int] = None,
    ) -> List[Tweet]:
        try:
            args = ["list-timeline", list_id_or_url, "-n", str(limit), "--json"]
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            return self._parse_list_timeline_output(out)[:limit]
        except Exception as e:
            self.logger.error(f"Bird get_list_timeline failed: {e}")
            return []

    async def get_following(
        self,
        user_id_or_handle: Optional[str] = None,
        limit: int = 20,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            args = ["following", "-n", str(limit), "--json"]
            if user_id_or_handle:
                args.extend(["--user", user_id_or_handle])
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            data = json.loads(out) if out.strip() else {}
            return self._extract_user_list(data)
        except Exception as e:
            self.logger.error(f"Bird get_following failed: {e}")
            return []

    async def get_followers(
        self,
        user_id_or_handle: Optional[str] = None,
        limit: int = 20,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            args = ["followers", "-n", str(limit), "--json"]
            if user_id_or_handle:
                args.extend(["--user", user_id_or_handle])
            if max_pages is not None:
                args.extend(["--max-pages", str(max_pages)])
            out = await self._run_command_async(args)
            data = json.loads(out) if out.strip() else {}
            return self._extract_user_list(data)
        except Exception as e:
            self.logger.error(f"Bird get_followers failed: {e}")
            return []

    async def get_user_about(self, handle: str) -> Optional[Dict[str, Any]]:
        try:
            h = handle if handle.startswith("@") else f"@{handle}"
            out = await self._run_command_async(["about", h, "--json"])
            data = json.loads(out) if out.strip() else {}
            return data.get("aboutProfile", data) if data else None
        except Exception as e:
            self.logger.error(f"Bird get_user_about failed: {e}")
            return None
