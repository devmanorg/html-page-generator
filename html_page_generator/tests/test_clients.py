from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch

from html_page_generator import AsyncDeepseekClient, AsyncPageGenerator, AsyncUnsplashClient


@pytest.fixture
async def setup_clients() -> AsyncGenerator[None]:
    async with (
        AsyncUnsplashClient.setup("UNSPLASH_CLIENT_ID", timeout=3),
        AsyncDeepseekClient.setup("DEEPSEEK_API_KEY"),
    ):
        yield


@pytest.mark.asyncio
async def test_clients_setup(setup_clients: None) -> None:
    unsplash_1 = AsyncUnsplashClient.get_initialized_instance()
    unsplash_2 = AsyncUnsplashClient.get_initialized_instance()
    assert unsplash_1 is unsplash_2

    deepseek_1 = AsyncDeepseekClient.get_initialized_instance()
    deepseek_2 = AsyncDeepseekClient.get_initialized_instance()
    assert deepseek_1 is deepseek_2


@pytest.mark.asyncio
async def test_page_title_generating(setup_clients: None, monkeypatch: MonkeyPatch) -> None:
    generator = AsyncPageGenerator()

    value = httpx.Response(
        200,
        json={
            "choices":
                [
                    {
                        "message": {
                            "content": "Mocked site title",
                            "role": "agent",
                        },
                    },
                ],
        },
        request=httpx.Request("POST", ""),
    )
    mocker = AsyncMock(return_value=value)

    monkeypatch.setattr(
        "html_page_generator.AsyncDeepseekClient.send",
        mocker,
    )

    assert await generator.create_site_title("prompt") == "Mocked site title"
