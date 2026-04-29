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
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Tweet:
    """Represents a tweet from Bird CLI JSON output."""
    id: str
    text: str
    author: str
    created_at: str
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tweet":
        """Create Tweet from Bird CLI JSON (author can be object {username, name} or string)."""
        author = data.get("author", "")
        if isinstance(author, dict):
            author = author.get("username", author.get("name", ""))
            if author and not author.startswith("@"):
                author = f"@{author}"
        elif not isinstance(author, str):
            author = str(author) if author else ""
        return cls(
            id=str(data.get("id", "")),
            text=data.get("text", ""),
            author=author,
            created_at=data.get("createdAt") or data.get("created_at", ""),
            likes=int(data.get("likeCount", data.get("likes", 0))),
            retweets=int(data.get("retweetCount", data.get("retweets", 0))),
            replies=int(data.get("replyCount", data.get("replies", 0))),
            url=data.get("url", ""),
        )


@dataclass
class Reply(Tweet):
    """A tweet that is a reply; extends Tweet with reply metadata."""
    in_reply_to_status_id: Optional[str] = None
    conversation_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reply":
        """Create Reply from Bird CLI JSON (reply fields: inReplyToStatusId, conversationId)."""
        base = Tweet.from_dict(data)
        in_reply = data.get("inReplyToStatusId") or data.get("in_reply_to_status_id")
        conv_id = data.get("conversationId") or data.get("conversation_id")
        return cls(
            id=base.id,
            text=base.text,
            author=base.author,
            created_at=base.created_at,
            likes=base.likes,
            retweets=base.retweets,
            replies=base.replies,
            url=base.url,
            in_reply_to_status_id=str(in_reply) if in_reply is not None else None,
            conversation_id=str(conv_id) if conv_id is not None else None,
        )


@dataclass
class Like:
    """A liked tweet with optional like metadata."""
    tweet: Tweet
    liked_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Like":
        """Create Like from Bird CLI JSON (tweet + optional likedAt)."""
        tweet = Tweet.from_dict(data)
        liked_at = data.get("likedAt") or data.get("liked_at")
        return cls(
            tweet=tweet,
            liked_at=str(liked_at) if liked_at is not None else None,
        )


@dataclass
class Bookmark:
    """A bookmarked tweet with optional folder and timestamp."""
    tweet: Tweet
    folder_id: Optional[str] = None
    bookmarked_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bookmark":
        """Create Bookmark from Bird CLI JSON (tweet + optional folderId, bookmarkedAt)."""
        tweet = Tweet.from_dict(data)
        folder_id = data.get("folderId") or data.get("folder_id")
        bookmarked_at = data.get("bookmarkedAt") or data.get("bookmarked_at")
        return cls(
            tweet=tweet,
            folder_id=str(folder_id) if folder_id is not None else None,
            bookmarked_at=str(bookmarked_at) if bookmarked_at is not None else None,
        )


@dataclass
class NewsItem:
    """A news/trending item from Bird CLI news output."""
    id: str = ""
    title: str = ""
    url: str = ""
    summary: str = ""
    source: str = ""
    published_at: str = ""
    raw: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        """Create NewsItem from Bird CLI JSON; missing keys use empty string."""
        return cls(
            id=str(data.get("id", data.get("_id", ""))),
            title=str(data.get("title", data.get("headline", ""))),
            url=str(data.get("url", data.get("link", ""))),
            summary=str(data.get("summary", data.get("description", ""))),
            source=str(data.get("source", "")),
            published_at=str(data.get("publishedAt", data.get("published_at", data.get("date", "")))),
            raw=data,
        )


