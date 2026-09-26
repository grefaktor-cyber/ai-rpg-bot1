from gigachat import GigaChat
import asyncio
import logging

SYSTEM_PROMPT = """Ты — мастер интерактивной RPG. Ведёшь игрока по вымышленному миру.

СТРОГИЕ ЗАПРЕТЫ (нарушение = отказ):
- Не упоминай реальных политиков, партии, действующих государственных деятелей.
- Не описывай реальные политические события, выборы, протесты, военные конфликты.
- Не пропагандируй наркотики, суицид, насилие, экстремизм, терроризм.
- Не генерируй инструкции по изготовлению оружия, взрывчатки, наркотиков.
- Не разжигай ненависть по признаку пола, расы, религии, национальности.
- Не пиши дезинформацию о реальных событиях.
- Если игрок просит запрещённое — вежливо откажись и переведи сюжет в безопасное русло.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Заканчивай выбором или вопросом.
- Помни всё, что игрок делал раньше.
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон",
    "суицид", "самоубийств", "убить себя", "покончить с собой",
    "теракт", "взорвать", "бомба", "взрывчатк", "оружие массового",
    "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

_client = None

def _get_client():
    global _client
    if _client is None:
        from config import GIGACHAT_CREDENTIALS
        _client = GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            verify_ssl_certs=False,
            model="GigaChat-2",
        )
    return _client

def _is_blocked(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)

async def generate(story, user_action):
    if _is_blocked(user_action):
        return ("🚫 Этот запрос нарушает правила игры. Я могу вести только "
                "безопасные сюжеты. Попробуй другое действие — например, "
                "«осматриваюсь» или «иду в лес».")

    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}\n\nИГРОК: {user_action}\n\nМАСТЕР:"

    def _sync_call():
        client = _get_client()
        response = client.chat({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            "temperature": 0.7,
            "max_tokens": 400,
        })
        return response.choices[0].message.content

    loop = asyncio.get_event_loop()
    try:
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _sync_call),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        return "⏳ Нейросеть не ответила за 30 секунд. Попробуй ещё раз."
    except Exception as e:
        logging.error(f"GigaChat error: {e}")
        return "⚠️ Ошибка нейросети. Попробуй позже."

    if _is_blocked(text):
        return ("🚫 Сюжет ушёл в недопустимую тему. Давай вернёмся в безопасное "
                "русло. Опиши, что делает герой.")

    return text
