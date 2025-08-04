import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from io import StringIO

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, create_react_agent
from pydantic import BaseModel

from ._async_deepseek_client import AsyncDeepseekClient
from ._unsplash_api_client import get_images

FIND_IMAGES_PROMPT = (
    "Ты получил запрос: '{user_prompt}', выбери из этого запроса 1-5 ключевых слов тематики,"
    "которые лягут в основу сайта, используя список этих слов, найди с помощью"
    "get_images_from_unsplash список url с картинками."
    "Со списком url ничего делать не нужно,"
    "эти url с картинками понадобятся в следующем запросе."
)

GENERATE_HTML_PROMPT = (
    "Ты -- разработчик фронтенда"
    "Содержимое ответа должно быть возможно вставить в HTML-файл без дополнительной редактуры."
    "Страница должна иметь анимированные заголовки, паралакс фона и другие визуальные украшения, если"
    "в запросе не указано прямо, что 'сайт должен быть без анимаций'."
    "В запрос может входить список ссылок на изображения,"
    "которые ты должен использовать при генерации сайта."
    "Если картинок не было передано или их оказалось недостаточно,"
    "то используй картинки из списка полученные ранее."
    "Не используй форматирование при выводе в виде ```html в начале и ``` в конце текста"
    "В ответе нужно будет присылать ТОЛЬКО сам код HTML+CSS+JS без дополнительных пояснений."
    "Полагаясь на системный промпт описанный выше обработай запрос: '{user_prompt}'."
    "Сейчас {current_year} год."
    "На выходе нужен чистый HTML+CSS+JS без пояснений."
    "Не используй форматирование при выводе в виде ```html в начале и ``` в конце текста."
)

CHECK_HTML_PROMPT = (
    "Проверь качество сгенерированной страницы. "
    "Проверь ссылки на все картинки в html, они не должны возвращать 404. "
    "Если всё хорошо, то верни ответ 'да', если нужно перегенерировать, то верни ответ 'нет'. "
    "Больше ничего возвращать не нужно."
)

REGENERATE_HTML_PROMPT = (
    "Проверь качество сгенерированной страницы. "
    "Сгенерируй новую с учетом всех возможных улучшений. "
    "Не используй форматирование при выводе в виде ```html в начале и ``` в конце текста"
    "В ответе нужно будет присылать ТОЛЬКО сам код HTML+CSS+JS без дополнительных пояснений."
    "Полагаясь на системный промпт описанный выше обработай запрос: '{user_prompt}'."
    "На выходе нужен чистый HTML+CSS+JS без пояснений."
    "Не используй форматирование при выводе в виде ```html в начале и ``` в конце текста."
)

SITE_TITLE_PROMPT = (
    "Придумай название ориентируясь на тематику запроса: '{user_prompt}'. "
    "Название должно содержать не более 3 слов, разделенных пробелами. "
    "В ответе пришли только придуманное название и ничего больше."
)


class HtmlPage(BaseModel):
    html_code: str = ""
    title: str = ""
    is_valid: bool = False


class AsyncPageGenerator:

    def __init__(self, *, debug_mode: bool = False) -> None:
        self.html_page = HtmlPage()
        self.current_year = datetime.now().year

        http_async_client = AsyncDeepseekClient.get_initialized_instance()
        model = ChatDeepSeek(
            model="deepseek-chat",
            api_key=http_async_client.deepseek_api_key,
            http_async_client=http_async_client,
            api_base=http_async_client.deepseek_base_url,
        )
        self.agent = create_react_agent(
            model,
            tools=ToolNode([get_images_from_unsplash]),
            checkpointer=InMemorySaver(),
            debug=debug_mode,
        )
        self.config: RunnableConfig = {
            "configurable": {
                "thread_id": uuid.uuid4().hex,
            },
        }

    async def __call__(self, user_prompt: str) -> AsyncGenerator[str]:
        yield await self.create_site_title(user_prompt)
        yield "\n"

        async for chunk in self.search_images(user_prompt):
            yield chunk
        yield "\n"

        async for chunk in self.generate_html(user_prompt):
            yield chunk
        yield "\n"

        yield await self.check_html()
        yield "\n"

        if not self.html_page.is_valid:
            async for chunk in self.regenerate_html():
                yield chunk

    async def search_images(self, user_prompt: str) -> AsyncGenerator[str]:
        message: dict = {
            "role": "user",
            "content": FIND_IMAGES_PROMPT.format(
                user_prompt=user_prompt,
            ),
        }
        ready_messages = {
            "messages": [message],
            "temperature": 0.1,
        }

        async_stream = self.agent.astream(
            input=ready_messages,
            config=self.config,
            stream_mode="messages",
        )
        async for token, _ in async_stream:
            yield token.content

    async def generate_html(self, user_prompt: str) -> AsyncGenerator[str]:
        message = {
            "role": "user",
            "content": GENERATE_HTML_PROMPT.format(user_prompt=user_prompt, current_year=self.current_year),
        }
        ready_messages = {
            "messages": [message],
            "temperature": 2,
        }
        async_stream = self.agent.astream(
            input=ready_messages,
            config=self.config,
            stream_mode="messages",
        )
        with StringIO() as buffer:
            async for token, _ in async_stream:
                yield token.content
                buffer.write(token.content)

            self.html_page.html_code = buffer.getvalue()

    async def check_html(self) -> str:
        message = {
            "role": "user",
            "content": CHECK_HTML_PROMPT,
        }
        ready_messages = {
            "messages": [message],
            "temperature": 0.1,
        }
        response = await self.agent.ainvoke(input=ready_messages, config=self.config)
        ai_answer = response["messages"][-1].content

        if 'да' in ai_answer.lower():
            self.html_page.is_valid = True
        return ai_answer

    async def regenerate_html(self) -> AsyncGenerator[str]:
        message = {
            "role": "user",
            "content": REGENERATE_HTML_PROMPT,
        }
        ready_messages = {
            "messages": [message],
            "temperature": 2,
        }
        async_stream = self.agent.astream(
            input=ready_messages,
            config=self.config,
            stream_mode="messages",
        )

        with StringIO() as buffer:
            async for token, _ in async_stream:
                yield token.content
                buffer.write(token.content)

            self.html_page.html_code = buffer.getvalue()

    async def create_site_title(self, user_prompt: str) -> str:
        message = {
            "role": "user",
            "content": SITE_TITLE_PROMPT.format(user_prompt=user_prompt),
        }
        ready_messages = {
            "messages": [message],
            "temperature": 2,
        }
        response = await self.agent.ainvoke(input=ready_messages, config=self.config)
        title = response["messages"][-1].content
        self.html_page.title = title
        return title


@tool
async def get_images_from_unsplash(topic_keywords: list[str]) -> list[str]:
    """
    Делает запрос к unsplash api для поиска картинок по переданным ключевым словам тематики.
    Возвращает список url картинок.
    """
    return await get_images(topic_keywords)
