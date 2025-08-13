# HTML Page Generator

Библиотека для генерации HTML страниц с помощью ИИ. Пользователю достаточно описать своими словами страницу,
которую он хочет получить. ИИ сами подберут изображения и напишут код страницы.

Работает с двумя сервисами:
- Unsplash - для поиска подходящих картинок.
- Deepseek - для управления процессом и собственно генерации кода страницы.

## Установка

Вы можете установить библиотеку с помощью `pip`:
```shell
# Установить из публичного GitHub репозитория (рекомендуемый способ)
$ pip install git+https://github.com/devmanorg/html-page-generator.git

# Установить из приватного GitLab репозитория (если у вас есть к нему доступ)
$ pip install git+https://gitlab.dvmn.org/dvmn/courses/fastapi/html-page-generator.git
```

## Подготовка

Понадобятся ключи для сервисов:

- `DEEPSEEK_API_KEY` - API-ключ аутентификации. [Получить](https://api-docs.deepseek.com/).
- `UNSPLASH_CLIENT_ID` - `Access Key` созданного Unsplash приложения. [Получить](https://unsplash.com/documentation#creating-a-developer-account).

Если вы используете альтернативную инсталляцию DeepSeek, то необходимо также указать её URL-адрес и, если это необходимо, другую LLM-модель:
- `DEEPSEEK_BASE_URL` - URL-адрес альтернативной инсталляции для запросов к API.

  Если не указан, то по-умолчанию используется URL-адрес официальной [DeepSeek API](https://api-docs.deepseek.com/).

- `DEEPSEEK_MODEL` - название альтернативной модели.
  
  Если не указано, то по-умолчанию используется модель `deepseek-chat`.

## Инициализация

На самом верхнем уровне приложения в момент запуска необходимо проинициализировать 2 клиентских класса.
Делается это для того, чтобы все запросы при работе приложения отправлялись в одной сессии.
Это сэкономит ресурсы, а также защитит от возможного бана со стороны сервисов при многократных обращениях.

```python
from html_page_generator import AsyncDeepseekClient, AsyncUnsplashClient


async def main():
    async with (
        AsyncUnsplashClient.setup("UNSPLASH_CLIENT_ID", timeout=3),
        AsyncDeepseekClient.setup(
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_BASE_URL",
            "DEEPSEEK_MODEL",
        ),
    ):
        ...
```
Замените `"UNSPLASH_CLIENT_ID"` и `"DEEPSEEK_API_KEY"` на ваши ключи доступа.

Если вы используете альтернативную инсталляцию DeepSeek, замените `"DEEPSEEK_BASE_URL"` и `"DEEPSEEK_MODEL"` на данные вашей инсталляции.

Если вы используете официальный [DeepSeek API](https://api-docs.deepseek.com/), то `"DEEPSEEK_BASE_URL"` и `"DEEPSEEK_MODEL"` можно не указывать.

## Генерация

Для запуска генерации используйте класс `AsyncPageGenerator`.
Объект этого класса при вызове возвращает асинхронный итератор, который будет стримить весь чат с нейросетью.
Таким образом можно отследить все, что происходит в процессе генерации.

```python
from html_page_generator import AsyncPageGenerator
import os

DEBUG_MODE = os.getenv("DEBUG_MODE", False)

async def generate_page(user_prompt: str):
    generator = AsyncPageGenerator(debug_mode=DEBUG_MODE)
    async for chunk in generator(user_prompt):
        print(chunk, end="", flush=True)

    with open(generator.html_page.title + '.html', 'w') as f:
        f.write(generator.html_page.html_code)

    print('Файл успешно сохранён!')
```

При значении параметра `debug_mode=True`, генератор будет логировать в консоль все действия агента.
Готовую страницу можно получить после генерации, в атрибуте `generator.html_page`.
Это объект класса `HtmlPage`, содержащий код страницы и `title`.

```python
class HtmlPage(BaseModel):
    html_code: str = ""
    title: str = ""
```

### Этапы генерации

Сначала нейросеть придумает название для сайта.

> *Note: Сразу после этой стадии в атрибуте `generator.html_page.title` можно получить заголовок страницы,
> не дожидаясь окончания генерации. Отслеживать этот момент можно, проверяя этот атрибут на каждой итерации.*

```python
generator = AsyncPageGenerator()
title_saved = False
async for chunk in generator(user_prompt):
    if title_saved:
        continue
    if title := generator.html_page.title:
        print(title)
        title_saved = True
```

Вторым этапом пойдет поиск подходящих изображений с помощью Unsplash.

Далее Deepseek сгенерирует код страницы.

И наконец на четвертом этапе Deepseek пройдется по коду еще раз и попробует его улучшить.
