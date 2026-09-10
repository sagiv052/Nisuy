import asyncio
import time
from typing import Any, Optional

import httpx


HEBREW_TRANSLITERATION = {
    "א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "u",
    "ז": "z", "ח": "h", "ט": "t", "י": "i", "כ": "k", "ך": "k",
    "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
    "ע": "a", "פ": "f", "ף": "f", "צ": "ts", "ץ": "ts", "ק": "k",
    "ר": "r", "ש": "sh", "ת": "t",
}


def transliterate_hebrew(text: str) -> str:
    """Create a practical Latin fallback for Hebrew title searches."""
    words: list[str] = []
    for word in text.strip().split():
        transliterated = "".join(HEBREW_TRANSLITERATION.get(character, character) for character in word)
        if word.endswith("ה") and transliterated.endswith("h"):
            transliterated = transliterated[:-1] + "a"
        words.append(transliterated)
    return " ".join(words)


class TMDBClient:
    def __init__(self, access_token: str = "", api_key: str = "") -> None:
        self.access_token = access_token
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_url = "https://image.tmdb.org/t/p/w1280"
        self._cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
        self.cache_ttl = 900.0

    @property
    def enabled(self) -> bool:
        return bool(self.access_token or self.api_key)

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}
        request_params = dict(params)
        if self.api_key:
            request_params["api_key"] = self.api_key
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
                    response = await client.get(f"{self.base_url}{path}", params=request_params, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as error:
                last_error = error
                if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500:
                    raise
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2 ** attempt))
        raise RuntimeError("TMDB temporarily unavailable") from last_error

    async def search(self, query: str, kind: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        query = query.strip()
        if not query:
            return []
        cache_key = (kind, query.casefold())
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return cached[1]
        endpoint = "/search/tv" if kind == "series" else "/search/movie"
        params: dict[str, Any] = {
            "query": query,
            "language": "he-IL",
            "include_adult": "false",
            "page": 1,
        }
        data = await self._get(endpoint, params)
        results = data.get("results", [])
        if not results:
            params["language"] = "en-US"
            data = await self._get(endpoint, params)
            results = data.get("results", [])
        if not results:
            transliterated = transliterate_hebrew(query)
            if transliterated != query:
                params["query"] = transliterated
                data = await self._get(endpoint, params)
                results = data.get("results", [])
        normalized = [self._normalize_result(result, kind) for result in results[:5]]
        self._cache[cache_key] = (time.monotonic(), normalized)
        return normalized

    async def details(self, tmdb_id: int, kind: str) -> dict[str, Any]:
        endpoint = f"/{'tv' if kind == 'series' else 'movie'}/{tmdb_id}"
        data = await self._get(endpoint, {
            "language": "he-IL",
            "append_to_response": "translations",
        })
        return self._normalize_result(data, kind)

    def _normalize_result(self, result: dict[str, Any], kind: str) -> dict[str, Any]:
        title = result.get("name" if kind == "series" else "title") or result.get("original_name") or result.get("original_title") or ""
        date = result.get("first_air_date" if kind == "series" else "release_date") or ""
        overview = result.get("overview") or ""
        poster_path = result.get("poster_path")
        backdrop_path = result.get("backdrop_path")
        return {
            "tmdb_id": result.get("id"),
            "title": title,
            "summary": overview,
            "release_year": int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None,
            "rating": result.get("vote_average"),
            "poster_url": f"{self.image_url}{poster_path}" if poster_path else "",
            "backdrop_url": f"{self.image_url}{backdrop_path}" if backdrop_path else "",
            "genre": ", ".join(
                genre.get("name", "") for genre in result.get("genres", []) if genre.get("name")
            ),
        }


async def search_tmdb(query: str, kind: str, access_token: str, api_key: str) -> list[dict[str, Any]]:
    return await TMDBClient(access_token, api_key).search(query, kind)
