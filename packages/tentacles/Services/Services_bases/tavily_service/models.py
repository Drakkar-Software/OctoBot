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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Usage:
    credits: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Usage":
        if not data or not isinstance(data, dict):
            return cls(credits=0)
        return cls(credits=int(data.get("credits", 0)))


@dataclass
class SearchResult:
    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0
    raw_content: Optional[str] = None
    favicon: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            title=str(data.get("title", "")),
            url=str(data.get("url", "")),
            content=str(data.get("content", "")),
            score=float(data.get("score", 0)),
            raw_content=data.get("raw_content"),
            favicon=data.get("favicon"),
        )


@dataclass
class SearchResponse:
    query: str = ""
    answer: Optional[str] = None
    images: Optional[List[Any]] = None
    results: List[SearchResult] = field(default_factory=list)
    response_time: Optional[float] = None
    auto_parameters: Optional[Dict[str, Any]] = None
    usage: Optional[Usage] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResponse":
        if not data or not isinstance(data, dict):
            return cls()
        results = [
            SearchResult.from_dict(r)
            for r in data.get("results", [])
            if isinstance(r, dict)
        ]
        usage_data = data.get("usage")
        usage = Usage.from_dict(usage_data) if usage_data else None
        return cls(
            query=str(data.get("query", "")),
            answer=data.get("answer"),
            images=data.get("images"),
            results=results,
            response_time=data.get("response_time"),
            auto_parameters=data.get("auto_parameters"),
            usage=usage,
            request_id=data.get("request_id"),
        )


@dataclass
class ExtractResult:
    url: str = ""
    raw_content: str = ""
    images: Optional[List[Any]] = None
    favicon: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractResult":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            url=str(data.get("url", "")),
            raw_content=str(data.get("raw_content", "")),
            images=data.get("images"),
            favicon=data.get("favicon"),
        )


@dataclass
class ExtractResponse:
    results: List[ExtractResult] = field(default_factory=list)
    failed_results: Optional[List[Any]] = None
    response_time: Optional[float] = None
    usage: Optional[Usage] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractResponse":
        if not data or not isinstance(data, dict):
            return cls()
        results = [
            ExtractResult.from_dict(r)
            for r in data.get("results", [])
            if isinstance(r, dict)
        ]
        usage_data = data.get("usage")
        usage = Usage.from_dict(usage_data) if usage_data else None
        return cls(
            results=results,
            failed_results=data.get("failed_results"),
            response_time=data.get("response_time"),
            usage=usage,
            request_id=data.get("request_id"),
        )


@dataclass
class CrawlResult:
    url: str = ""
    raw_content: str = ""
    favicon: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrawlResult":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            url=str(data.get("url", "")),
            raw_content=str(data.get("raw_content", "")),
            favicon=data.get("favicon"),
        )


@dataclass
class CrawlResponse:
    base_url: str = ""
    results: List[CrawlResult] = field(default_factory=list)
    response_time: Optional[float] = None
    usage: Optional[Usage] = None
    request_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CrawlResponse":
        if not data or not isinstance(data, dict):
            return cls()
        results = [
            CrawlResult.from_dict(r)
            for r in data.get("results", [])
            if isinstance(r, dict)
        ]
        usage_data = data.get("usage")
        usage = Usage.from_dict(usage_data) if usage_data else None
        return cls(
            base_url=str(data.get("base_url", "")),
            results=results,
            response_time=data.get("response_time"),
            usage=usage,
            request_id=data.get("request_id"),
        )


@dataclass
class ResearchTask:
    request_id: str = ""
    created_at: Optional[str] = None
    status: str = ""
    input: str = ""
    model: Optional[str] = None
    response_time: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchTask":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            request_id=str(data.get("request_id", "")),
            created_at=data.get("created_at"),
            status=str(data.get("status", "")),
            input=str(data.get("input", "")),
            model=data.get("model"),
            response_time=data.get("response_time"),
        )


@dataclass
class ResearchResult:
    answer: Optional[str] = None
    sources: Optional[List[Any]] = None
    request_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchResult":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            answer=data.get("answer"),
            sources=data.get("sources"),
            request_id=data.get("request_id"),
            raw=data,
        )
