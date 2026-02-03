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
import aiohttp
from typing import Any, Dict, List, Optional, Sequence

import octobot_services.constants as services_constants
import octobot_services.services as services


class SearXNGService(services.AbstractWebSearchService):
    """
    SearXNG web search service implementation.

    SearXNG is a free, privacy-respecting metasearch engine.
    See: https://github.com/searxng/searxng
    
    Connects to a self-hosted SearXNG instance to perform web searches.
    SearXNG is a privacy-respecting metasearch engine that aggregates
    results from multiple search engines.
    
    Configuration:
        - url: Base URL of the SearXNG instance (e.g., "http://localhost")
        - port: Port number (e.g., 8080)
        - categories: Default search categories (e.g., ["general", "news"])
        - language: Default language code (e.g., "en")
        - time_range: Default time range filter
        - safe_search: Safe search level (0=off, 1=moderate, 2=strict)
        - engines: Comma-separated list of engines to use
    """

    SEARXNG_DOCS_URL = "https://docs.searxng.org/"
    SEARXNG_GITHUB_URL = "https://github.com/searxng/searxng"

    def __init__(self):
        super().__init__()
        self._base_url: Optional[str] = None
        self._port: Optional[int] = None
        self._default_categories: Optional[List[str]] = None
        self._default_language: Optional[str] = None
        self._default_time_range: Optional[str] = None
        self._safe_search: int = 0
        self._default_engines: Optional[str] = None

    def _get_api_url(self) -> str:
        if not self._base_url:
            return ""
        url = self._base_url.rstrip("/")
        if self._port:
            url = f"{url}:{self._port}"
        return url

    async def _get(self, path: str, params: Dict[str, Any], timeout: float = 30) -> Dict[str, Any]:
        url = f"{self._get_api_url()}/{path.lstrip('/')}"
        if not url or not self._base_url:
            self.logger.error("SearXNG URL not configured")
            return {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        self.logger.error(
                            f"SearXNG API error {resp.status}: {text[:200]}"
                        )
                        return {}
                    return await resp.json()
        except aiohttp.ClientError as e:
            self.logger.exception(e, True, f"SearXNG API request failed: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"SearXNG API error: {e}")
            return {}

    def get_type(self):
        return services_constants.CONFIG_SEARXNG

    def get_endpoint(self):
        return self

    @staticmethod
    def is_setup_correctly(config):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in config
            and services_constants.CONFIG_SEARXNG
            in config[services_constants.CONFIG_CATEGORY_SERVICES]
            and services_constants.CONFIG_SERVICE_INSTANCE
            in config[services_constants.CONFIG_CATEGORY_SERVICES][
                services_constants.CONFIG_SEARXNG
            ]
        )

    def has_required_configuration(self):
        return (
            services_constants.CONFIG_CATEGORY_SERVICES in self.config
            and services_constants.CONFIG_SEARXNG
            in self.config[services_constants.CONFIG_CATEGORY_SERVICES]
            and self.check_required_config(
                self.config[services_constants.CONFIG_CATEGORY_SERVICES][
                    services_constants.CONFIG_SEARXNG
                ]
            )
        )

    async def prepare(self):
        searxng_config = self.config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(
            services_constants.CONFIG_SEARXNG, {}
        )
        
        self._base_url = (
            searxng_config.get(services_constants.CONFIG_SEARXNG_URL) or ""
        ).strip() or None
        
        port_str = str(searxng_config.get(services_constants.CONFIG_SEARXNG_PORT) or "").strip()
        self._port = int(port_str) if port_str.isdigit() else None
        
        categories = searxng_config.get(services_constants.CONFIG_SEARXNG_CATEGORIES)
        if isinstance(categories, str):
            self._default_categories = [c.strip() for c in categories.split(",") if c.strip()]
        elif isinstance(categories, list):
            self._default_categories = categories
        else:
            self._default_categories = None
        
        self._default_language = (
            searxng_config.get(services_constants.CONFIG_SEARXNG_LANGUAGE) or ""
        ).strip() or None
        
        self._default_time_range = (
            searxng_config.get(services_constants.CONFIG_SEARXNG_TIME_RANGE) or ""
        ).strip() or None
        
        safe_str = str(searxng_config.get(services_constants.CONFIG_SEARXNG_SAFE_SEARCH) or "0").strip()
        self._safe_search = int(safe_str) if safe_str.isdigit() else 0
        
        self._default_engines = (
            searxng_config.get(services_constants.CONFIG_SEARXNG_ENGINES) or ""
        ).strip() or None

        # Test connection
        if self._base_url:
            try:
                # SearXNG returns JSON when format=json is specified
                test_result = await self._get("search", {"q": "test", "format": "json"}, timeout=10)
                self._startup_healthy = bool(test_result)
                self._startup_message = (
                    f"SearXNG connected at {self._get_api_url()}" 
                    if self._startup_healthy 
                    else ""
                )
            except Exception as e:
                self._startup_healthy = False
                self._startup_message = ""
                self.logger.warning(f"SearXNG connection test failed: {e}")
        else:
            self._startup_healthy = False
            self._startup_message = ""

    def get_fields_description(self):
        return {
            services_constants.CONFIG_SEARXNG_URL: "SearXNG instance URL (e.g., http://localhost or https://searxng.example.com).",
            services_constants.CONFIG_SEARXNG_PORT: "Port number (optional, e.g., 8080).",
            services_constants.CONFIG_SEARXNG_CATEGORIES: "Default search categories (comma-separated, e.g., 'general,news').",
            services_constants.CONFIG_SEARXNG_LANGUAGE: "Default language code (e.g., 'en', 'fr', 'de').",
            services_constants.CONFIG_SEARXNG_TIME_RANGE: "Default time range filter (e.g., 'day', 'week', 'month', 'year').",
            services_constants.CONFIG_SEARXNG_SAFE_SEARCH: "Safe search level: 0=off, 1=moderate, 2=strict.",
            services_constants.CONFIG_SEARXNG_ENGINES: "Engines to use (comma-separated, e.g., 'google,bing,duckduckgo').",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_SEARXNG_URL: "http://localhost",
            services_constants.CONFIG_SEARXNG_PORT: "8080",
            services_constants.CONFIG_SEARXNG_CATEGORIES: "general",
            services_constants.CONFIG_SEARXNG_LANGUAGE: "en",
            services_constants.CONFIG_SEARXNG_TIME_RANGE: "",
            services_constants.CONFIG_SEARXNG_SAFE_SEARCH: "0",
            services_constants.CONFIG_SEARXNG_ENGINES: "",
        }

    def get_required_config(self):
        return [services_constants.CONFIG_SEARXNG_URL]

    @classmethod
    def get_help_page(cls) -> str:
        return cls.SEARXNG_DOCS_URL

    def get_website_url(self) -> str:
        return self.SEARXNG_GITHUB_URL

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
        engines: Optional[str] = None,
        safe_search: Optional[int] = None,
        **kwargs,
    ) -> services.WebSearchResponse:
        params: Dict[str, Any] = {
            "q": query,
            "format": "json",
        }
        
        cats = categories or self._default_categories
        if cats:
            params["categories"] = ",".join(cats) if isinstance(cats, (list, tuple)) else cats
        
        lang = language or self._default_language
        if lang:
            params["language"] = lang
        
        tr = time_range or self._default_time_range
        if tr:
            params["time_range"] = tr
        
        ss = safe_search if safe_search is not None else self._safe_search
        params["safesearch"] = ss
        
        eng = engines or self._default_engines
        if eng:
            params["engines"] = eng
        params.update(kwargs)
        
        request_timeout = timeout or self.DEFAULT_TIMEOUT
        raw = await self._get("search", params, timeout=request_timeout)
        
        if not raw:
            return services.WebSearchResponse(query=query)
        
        results: List[services.WebSearchResult] = []
        for r in raw.get("results", []):
            if not isinstance(r, dict):
                continue
            
            url = str(r.get("url", ""))
            
            if include_domains:
                if not any(domain in url for domain in include_domains):
                    continue
            if exclude_domains:
                if any(domain in url for domain in exclude_domains):
                    continue
            
            results.append(services.WebSearchResult(
                title=str(r.get("title", "")),
                url=url,
                content=str(r.get("content", "")),
                score=float(r.get("score", 0)),
                engine=r.get("engine"),
            ))
            
            # Limit results if max_results specified
            if max_results and len(results) >= max_results:
                break
        
        return services.WebSearchResponse(
            query=query,
            results=results,
            total_results=raw.get("number_of_results"),
        )

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
            categories=["news"],
            language=language,
            time_range=time_range or "week",  # Default to recent news
            timeout=timeout,
            **kwargs,
        )
