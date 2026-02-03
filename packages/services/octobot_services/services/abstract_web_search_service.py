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
import abc
import typing
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from octobot_services.services.abstract_service import AbstractService

@dataclass
class WebSearchResult:
    """Single web search result."""
    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0
    raw_content: Optional[str] = None
    favicon: Optional[str] = None
    engine: Optional[str] = None  # Which search engine returned this result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSearchResult":
        if not data or not isinstance(data, dict):
            return cls()
        return cls(
            title=str(data.get("title", "")),
            url=str(data.get("url", "")),
            content=str(data.get("content", "")),
            score=float(data.get("score", 0)),
            raw_content=data.get("raw_content"),
            favicon=data.get("favicon"),
            engine=data.get("engine"),
        )


@dataclass
class WebSearchResponse:
    """Web search response containing multiple results."""
    query: str = ""
    results: List[WebSearchResult] = field(default_factory=list)
    answer: Optional[str] = None  # AI-generated answer if available
    response_time: Optional[float] = None
    total_results: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebSearchResponse":
        if not data or not isinstance(data, dict):
            return cls()
        results = [
            WebSearchResult.from_dict(r)
            for r in data.get("results", [])
            if isinstance(r, dict)
        ]
        return cls(
            query=str(data.get("query", "")),
            results=results,
            answer=data.get("answer"),
            response_time=data.get("response_time"),
            total_results=data.get("total_results"),
        )


class AbstractWebSearchService(AbstractService, abc.ABC):
    """
    Abstract base class for web search services.
    
    Provides a common interface for web search functionality similar to
    how AbstractAIService provides a common interface for AI/LLM services.
    
    Implementations should override the abstract methods to provide
    search functionality via different backends (Tavily, SearXNG, etc.).
    """
    
    DEFAULT_MAX_RESULTS: int = 10
    DEFAULT_TIMEOUT: float = 30.0

    def __init__(self):
        super().__init__()
        self._startup_message: str = ""
        self._startup_healthy: bool = False

    @abc.abstractmethod
    async def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        categories: Optional[Sequence[str]] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> WebSearchResponse:
        """
        Perform a web search.
        
        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            categories: Search categories (e.g., ["general", "news", "images"]).
            language: Language code for results (e.g., "en", "fr").
            time_range: Time range filter (e.g., "day", "week", "month", "year").
            include_domains: Only include results from these domains.
            exclude_domains: Exclude results from these domains.
            timeout: Request timeout in seconds.
            **kwargs: Additional provider-specific parameters.
        
        Returns:
            WebSearchResponse containing the search results.
        """
        raise NotImplementedError("search not implemented")

    async def search_news(
        self,
        query: str,
        max_results: Optional[int] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> WebSearchResponse:
        """
        Search for news articles.
        
        Default implementation calls search() with categories=["news"].
        Override for providers with dedicated news search endpoints.
        
        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            language: Language code for results.
            time_range: Time range filter.
            timeout: Request timeout in seconds.
            **kwargs: Additional provider-specific parameters.
        
        Returns:
            WebSearchResponse containing news results.
        """
        raise NotImplementedError("search_news not implemented")

    def get_successful_startup_message(self) -> typing.Tuple[str, bool]:
        """Return startup message and health status."""
        return self._startup_message, self._startup_healthy
