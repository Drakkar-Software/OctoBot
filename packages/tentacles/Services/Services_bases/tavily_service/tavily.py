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
import aiohttp
from typing import Any, Dict, List, Optional, Sequence, Union

import octobot_services.constants as services_constants
import octobot_services.services as services

from .models import (
    CrawlResponse,
    ExtractResponse,
    ResearchResult,
    ResearchTask,
    SearchResponse,
    SearchResult,
)


TAVILY_API_BASE = "https://api.tavily.com"


class TavilyService(services.AbstractWebSearchService):

    TAVILY_DOCS_URL = "https://docs.tavily.com/documentation/api-reference/introduction"

    def __init__(self):
        super().__init__()
        self._api_key: Optional[str] = None
        self._headers: Dict[str, str] = {}

    async def _post(self, path: str, data: dict, timeout: float = 60) -> dict:
        if not self._api_key:
            if self.logger:
                self.logger.error("Tavily API key not set")
            return {}
        url = f"{TAVILY_API_BASE}/{path.lstrip('/')}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=data,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        if self.logger:
                            self.logger.error(
                                f"Tavily API error {resp.status}: {text[:200]}"
                            )
                        return {}
                    return await resp.json()
        except aiohttp.ClientError as e:
            if self.logger:
                self.logger.error(f"Tavily API request failed: {e}")
            return {}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Tavily API error: {e}")
            return {}

    async def _get(self, path: str, timeout: float = 30) -> dict:
        if not self._api_key:
            if self.logger:
                self.logger.error("Tavily API key not set")
            return {}
        url = f"{TAVILY_API_BASE}/{path.lstrip('/')}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        if self.logger:
                            self.logger.error(
                                f"Tavily API error {resp.status}: {text[:200]}"
                            )
                        return {}
                    return await resp.json()
        except aiohttp.ClientError as e:
            if self.logger:
                self.logger.error(f"Tavily API request failed: {e}")
            return {}
        except Exception as e:
            if self.logger:
                self.logger.error(f"Tavily API error: {e}")
            return {}

    def get_type(self):
        return services_constants.CONFIG_TAVILY

    def get_endpoint(self):
        return self

    @staticmethod
    def is_setup_correctly(config):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in config
            and services_constants.CONFIG_TAVILY
            in config[services_constants.CONFIG_CATEGORY_SERVICES]
            and services_constants.CONFIG_SERVICE_INSTANCE
            in config[services_constants.CONFIG_CATEGORY_SERVICES][
                services_constants.CONFIG_TAVILY
            ]
        )

    def has_required_configuration(self):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in self.config
            and services_constants.CONFIG_TAVILY
            in self.config[services_constants.CONFIG_CATEGORY_SERVICES]
            and self.check_required_config(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                    services_constants.CONFIG_TAVILY
                ]
            )
        )

    async def prepare(self):
        tavily_config = self.config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(
            services_constants.CONFIG_TAVILY, {}
        )
        self._api_key = (
            tavily_config.get(services_constants.CONFIG_TAVILY_API_KEY) or ""
        ).strip() or None
        self._headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"
        project_id = (
            tavily_config.get(services_constants.CONFIG_TAVILY_PROJECT_ID) or ""
        ).strip()
        if project_id:
            self._headers["X-Project-ID"] = project_id

        if self._api_key:
            check = await self._post("search", {"query": "test"}, timeout=15)
            self._startup_healthy = bool(check)
            self._startup_message = (
                "Tavily API ready." if self._startup_healthy else ""
            )
        else:
            self._startup_healthy = False
            self._startup_message = ""

    def get_successful_startup_message(self):
        return self._startup_message, self._startup_healthy

    def get_fields_description(self):
        return {
            services_constants.CONFIG_TAVILY_API_KEY: "Tavily API key (from app.tavily.com).",
            services_constants.CONFIG_TAVILY_PROJECT_ID: "Optional X-Project-ID for request tracking.",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_TAVILY_API_KEY: "",
            services_constants.CONFIG_TAVILY_PROJECT_ID: "",
        }

    def get_required_config(self):
        return [services_constants.CONFIG_TAVILY_API_KEY]

    @classmethod
    def get_help_page(cls) -> str:
        return cls.TAVILY_DOCS_URL

    def get_website_url(self) -> str:
        return self.TAVILY_DOCS_URL

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
        # Tavily-specific parameters
        search_depth: Optional[str] = None,
        topic: Optional[str] = None,
        include_answer: Optional[Union[bool, str]] = None,
        include_raw_content: Optional[Union[bool, str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        include_images: Optional[bool] = None,
        country: Optional[str] = None,
        auto_parameters: Optional[bool] = None,
        include_favicon: Optional[bool] = None,
        include_usage: Optional[bool] = None,
        chunks_per_source: Optional[int] = None,
        **kwargs,
    ) -> services.WebSearchResponse:
        tavily_response = await self.search_tavily(
            query=query,
            search_depth=search_depth,
            topic=topic,
            max_results=max_results,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date,
            days=days,
            include_images=include_images,
            country=country,
            auto_parameters=auto_parameters,
            include_favicon=include_favicon,
            include_usage=include_usage,
            chunks_per_source=chunks_per_source,
            timeout=timeout or 60.0,
        )
        
        web_results = []
        for tavily_result in tavily_response.results:
            web_results.append(services.WebSearchResult(
                title=tavily_result.title,
                url=tavily_result.url,
                content=tavily_result.content,
                score=tavily_result.score,
                raw_content=tavily_result.raw_content,
                favicon=tavily_result.favicon,
            ))
        
        return services.WebSearchResponse(
            query=tavily_response.query,
            results=web_results,
            answer=tavily_response.answer,
            response_time=tavily_response.response_time,
            total_results=len(web_results),
        )

    async def search_tavily(
        self,
        query: str,
        search_depth: Optional[str] = None,
        topic: Optional[str] = None,
        max_results: Optional[int] = None,
        include_answer: Optional[Union[bool, str]] = None,
        include_raw_content: Optional[Union[bool, str]] = None,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        time_range: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: Optional[int] = None,
        include_images: Optional[bool] = None,
        country: Optional[str] = None,
        auto_parameters: Optional[bool] = None,
        include_favicon: Optional[bool] = None,
        include_usage: Optional[bool] = None,
        chunks_per_source: Optional[int] = None,
        timeout: float = 60,
    ) -> SearchResponse:
        data = {"query": query}
        if search_depth is not None:
            data["search_depth"] = search_depth
        if topic is not None:
            data["topic"] = topic
        if max_results is not None:
            data["max_results"] = max_results
        if include_answer is not None:
            data["include_answer"] = include_answer
        if include_raw_content is not None:
            data["include_raw_content"] = include_raw_content
        if include_domains is not None:
            data["include_domains"] = list(include_domains)
        if exclude_domains is not None:
            data["exclude_domains"] = list(exclude_domains)
        if time_range is not None:
            data["time_range"] = time_range
        if start_date is not None:
            data["start_date"] = start_date
        if end_date is not None:
            data["end_date"] = end_date
        if days is not None:
            data["days"] = days
        if include_images is not None:
            data["include_images"] = include_images
        if country is not None:
            data["country"] = country
        if auto_parameters is not None:
            data["auto_parameters"] = auto_parameters
        if include_favicon is not None:
            data["include_favicon"] = include_favicon
        if include_usage is not None:
            data["include_usage"] = include_usage
        if chunks_per_source is not None:
            data["chunks_per_source"] = chunks_per_source
        raw = await self._post("search", data, timeout=min(timeout, 120))
        return SearchResponse.from_dict(raw)

    async def search_news(
        self,
        query: str,
        max_results: Optional[int] = None,
        language: Optional[str] = None,
        time_range: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> services.WebSearchResponse:
        return await self.search(
            query=query,
            max_results=max_results,
            categories=None,  # Not used by Tavily
            language=language,
            time_range=time_range or "week",  # Default to recent news
            timeout=timeout,
            topic="news",  # Tavily-specific: use news topic
            **kwargs,
        )

    async def extract(
        self,
        urls: Union[List[str], str],
        include_images: Optional[bool] = None,
        extract_depth: Optional[str] = None,
        format: Optional[str] = None,
        timeout: float = 30,
        include_favicon: Optional[bool] = None,
        include_usage: Optional[bool] = None,
        query: Optional[str] = None,
        chunks_per_source: Optional[int] = None,
    ) -> ExtractResponse:
        data = {"urls": urls if isinstance(urls, list) else [urls]}
        if include_images is not None:
            data["include_images"] = include_images
        if extract_depth is not None:
            data["extract_depth"] = extract_depth
        if format is not None:
            data["format"] = format
        if timeout is not None:
            data["timeout"] = timeout
        if include_favicon is not None:
            data["include_favicon"] = include_favicon
        if include_usage is not None:
            data["include_usage"] = include_usage
        if query is not None:
            data["query"] = query
        if chunks_per_source is not None:
            data["chunks_per_source"] = chunks_per_source
        raw = await self._post("extract", data, timeout=timeout)
        return ExtractResponse.from_dict(raw)

    async def crawl(
        self,
        url: str,
        max_depth: Optional[int] = None,
        max_breadth: Optional[int] = None,
        limit: Optional[int] = None,
        instructions: Optional[str] = None,
        select_paths: Optional[Sequence[str]] = None,
        select_domains: Optional[Sequence[str]] = None,
        exclude_paths: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        allow_external: Optional[bool] = None,
        include_images: Optional[bool] = None,
        extract_depth: Optional[str] = None,
        format: Optional[str] = None,
        timeout: float = 150,
        include_favicon: Optional[bool] = None,
        include_usage: Optional[bool] = None,
        chunks_per_source: Optional[int] = None,
    ) -> CrawlResponse:
        data = {"url": url}
        if max_depth is not None:
            data["max_depth"] = max_depth
        if max_breadth is not None:
            data["max_breadth"] = max_breadth
        if limit is not None:
            data["limit"] = limit
        if instructions is not None:
            data["instructions"] = instructions
        if select_paths is not None:
            data["select_paths"] = list(select_paths)
        if select_domains is not None:
            data["select_domains"] = list(select_domains)
        if exclude_paths is not None:
            data["exclude_paths"] = list(exclude_paths)
        if exclude_domains is not None:
            data["exclude_domains"] = list(exclude_domains)
        if allow_external is not None:
            data["allow_external"] = allow_external
        if include_images is not None:
            data["include_images"] = include_images
        if extract_depth is not None:
            data["extract_depth"] = extract_depth
        if format is not None:
            data["format"] = format
        if timeout is not None:
            data["timeout"] = timeout
        if include_favicon is not None:
            data["include_favicon"] = include_favicon
        if include_usage is not None:
            data["include_usage"] = include_usage
        if chunks_per_source is not None:
            data["chunks_per_source"] = chunks_per_source
        raw = await self._post("crawl", data, timeout=min(timeout, 150))
        return CrawlResponse.from_dict(raw)

    async def map(
        self,
        url: str,
        max_depth: Optional[int] = None,
        max_breadth: Optional[int] = None,
        limit: Optional[int] = None,
        instructions: Optional[str] = None,
        select_paths: Optional[Sequence[str]] = None,
        select_domains: Optional[Sequence[str]] = None,
        exclude_paths: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        allow_external: Optional[bool] = None,
        include_images: Optional[bool] = None,
        timeout: float = 150,
        include_usage: Optional[bool] = None,
    ) -> CrawlResponse:
        data = {"url": url}
        if max_depth is not None:
            data["max_depth"] = max_depth
        if max_breadth is not None:
            data["max_breadth"] = max_breadth
        if limit is not None:
            data["limit"] = limit
        if instructions is not None:
            data["instructions"] = instructions
        if select_paths is not None:
            data["select_paths"] = list(select_paths)
        if select_domains is not None:
            data["select_domains"] = list(select_domains)
        if exclude_paths is not None:
            data["exclude_paths"] = list(exclude_paths)
        if exclude_domains is not None:
            data["exclude_domains"] = list(exclude_domains)
        if allow_external is not None:
            data["allow_external"] = allow_external
        if include_images is not None:
            data["include_images"] = include_images
        if timeout is not None:
            data["timeout"] = timeout
        if include_usage is not None:
            data["include_usage"] = include_usage
        raw = await self._post("map", data, timeout=min(timeout, 150))
        return CrawlResponse.from_dict(raw)

    async def research(
        self,
        input: str,
        model: Optional[str] = None,
        output_schema: Optional[dict] = None,
        stream: bool = False,
        citation_format: str = "numbered",
        timeout: Optional[float] = None,
    ) -> ResearchTask:
        data = {"input": input, "stream": stream, "citation_format": citation_format}
        if model is not None:
            data["model"] = model
        if output_schema is not None:
            data["output_schema"] = output_schema
        to = min(timeout or 120, 120)
        raw = await self._post("research", data, timeout=to)
        return ResearchTask.from_dict(raw)

    async def get_research(self, request_id: str) -> ResearchResult:
        raw = await self._get(f"research/{request_id}", timeout=30)
        return ResearchResult.from_dict(raw)

    async def get_search_context(
        self,
        query: str,
        search_depth: str = "basic",
        topic: str = "general",
        days: int = 7,
        max_results: int = 5,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        max_tokens: int = 4000,
        timeout: float = 60,
        country: Optional[str] = None,
        include_favicon: Optional[bool] = None,
    ) -> str:
        resp = await self.search(
            query,
            search_depth=search_depth,
            topic=topic,
            days=days,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=False,
            include_raw_content=False,
            timeout=timeout,
            country=country,
            include_favicon=include_favicon,
        )
        context = [
            {"url": r.url, "content": r.content}
            for r in resp.results
        ]
        return json.dumps(context)

    async def qna_search(
        self,
        query: str,
        search_depth: str = "advanced",
        topic: str = "general",
        days: int = 7,
        max_results: int = 5,
        include_domains: Optional[Sequence[str]] = None,
        exclude_domains: Optional[Sequence[str]] = None,
        timeout: float = 60,
        country: Optional[str] = None,
        include_favicon: Optional[bool] = None,
    ) -> str:
        resp = await self.search(
            query,
            search_depth=search_depth,
            topic=topic,
            days=days,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=True,
            timeout=timeout,
            country=country,
            include_favicon=include_favicon,
        )
        return resp.answer or ""

    async def get_company_info(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 5,
        timeout: float = 60,
        country: Optional[str] = None,
    ) -> List[SearchResult]:
        topics = ["news", "general", "finance"]
        responses = await asyncio.gather(
            *[
                self.search(
                    query,
                    search_depth=search_depth,
                    topic=topic,
                    max_results=max_results,
                    include_answer=False,
                    timeout=timeout,
                    country=country,
                )
                for topic in topics
            ]
        )
        all_results = [r for resp in responses for r in resp.results]
        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:max_results]
