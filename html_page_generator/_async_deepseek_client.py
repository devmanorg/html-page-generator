from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from langchain_deepseek.chat_models import DEFAULT_API_BASE
from pydantic import SecretStr

from ._exceptions import AsyncDeepseekClientError

DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"

class AsyncDeepseekClient(httpx.AsyncClient):
    _initialized_instance: Optional['AsyncDeepseekClient'] = None

    def __init__(
        self,
        deepseek_api_key: str | SecretStr,
        deepseek_base_url: str = DEFAULT_API_BASE,
        deepseek_model: str = DEFAULT_DEEPSEEK_MODEL,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_base_url = deepseek_base_url
        self.deepseek_model = deepseek_model

    @classmethod
    @asynccontextmanager
    async def setup(
        cls,
        deepseek_api_key: str | SecretStr,
        deepseek_base_url: str = DEFAULT_API_BASE,
        deepseek_model: str = DEFAULT_DEEPSEEK_MODEL,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[None]:
        cls._initialized_instance = cls(deepseek_api_key, deepseek_base_url, deepseek_model, *args, **kwargs)
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
