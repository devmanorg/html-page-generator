from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from pydantic import SecretStr

from ._exceptions import AsyncDeepseekClientError


class AsyncDeepseekClient(httpx.AsyncClient):
    _initialized_instance: Optional['AsyncDeepseekClient'] = None

    def __init__(self, deepseek_api_key: str | SecretStr, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.deepseek_api_key = deepseek_api_key

    @classmethod
    @asynccontextmanager
    async def setup(cls, deepseek_api_key: str | SecretStr, *args: Any, **kwargs: Any) -> AsyncGenerator[None]:
        cls._initialized_instance = cls(deepseek_api_key, *args, **kwargs)
        async with cls._initialized_instance:
            yield

    @classmethod
    def get_initialized_instance(cls) -> 'AsyncDeepseekClient':
        if client := cls._initialized_instance:
            return client
        raise AsyncDeepseekClientError(
            "Клиент AsyncDeepseekClient не был проинициализирован. "
            "Воспользуйтесь методом setup() для инициализации клиента.",
        )
