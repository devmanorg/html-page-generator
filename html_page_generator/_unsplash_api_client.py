from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Self

import httpx
from httpx import Response
from pydantic import SecretStr

from ._exceptions import UnsplashAsyncClientError

BASE_URL: str = "https://api.unsplash.com"


class AsyncUnsplashClient(httpx.AsyncClient):
    _initialized_instance = None

    def __init__(self, unsplash_client_id: str = "", *args: Any, **kwargs: Any) -> None:
        self.unsplash_client_id = unsplash_client_id
        kwargs["base_url"] = kwargs.get("base_url", BASE_URL)
        super().__init__(*args, **kwargs)

    @classmethod
    @asynccontextmanager
    async def setup(cls, unsplash_client_id: str | SecretStr, *args: Any, **kwargs: Any) -> AsyncGenerator[None]:
        if isinstance(unsplash_client_id, SecretStr):
            unsplash_client_id = unsplash_client_id.get_secret_value()
        cls._initialized_instance = cls(unsplash_client_id, *args, **kwargs)
        async with cls._initialized_instance:
            yield

    @classmethod
    def get_initialized_instance(cls) -> Self:
        if initialized_instance := cls._initialized_instance:
            return initialized_instance
        raise UnsplashAsyncClientError(
            "Клиент UnsplashAsyncClient не был проинициализирован. "
            "Воспользуйтесь методом setup() для инициализации клиента.",
        )

    async def request(self, *args: Any, **kwargs: Any) -> Response:
        params = kwargs.pop("params", {})
        params["client_id"] = self.unsplash_client_id
        return await super().request(*args, params=params, **kwargs)


async def get_images(keywords: list[str]) -> list[str]:
    client = AsyncUnsplashClient.get_initialized_instance()
    response = await client.get(
        "/search/photos",
        params={"query": ",".join(keywords)},
    )
    response.raise_for_status()
    payload = response.json()
    return [
        photo["urls"]["regular"]
        for photo in payload["results"]
    ]
