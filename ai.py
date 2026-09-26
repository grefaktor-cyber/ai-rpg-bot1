from gigachat import GigaChat
import asyncio
import logging
import re

SYSTEM_PROMPT = """Ты — мастер интерактивной RPG. Ведёшь игрока по вымышленному миру.

СТРОГИЕ ЗАПРЕТЫ:
- Не упоминай реальных политиков, партии, действующих государственных деятелей.
- Не описывай реальные политические события, выборы, протесты, военные конфликты.
- Не пропагандируй наркотики, суицид, насилие, экстремизм, терроризм.
- Не генерируй инструкции по изготовлению оружия, взрывчатки, наркотиков.
- Не разжигай ненависть по признаку пола, расы, религии, национальности.
- Если игрок просит запрещённое — вежливо откажись и переведи сюжет в безопасное русло.

Правила игры:
- Пиши ярко, коротко: 3-6 предложений.
- Заканчивай выбором или вопросом.
- Помни всё, что игрок делал раньше.

ТЕГИ (добавляй в конец ответа, если применимо):
- [ITEM: название] — если игрок нашёл/получил предмет.
- [LOCATION: название] — если игрок перешёл в новую локацию.
Не добавляй теги, если событие не произошло.
"""

BLOCKED_WORDS = [
    "наркотик", "героин", "кокаин", "мефедрон", "суицид", "самоубийств",
    "убить себя", "покончить с собой", "теракт", "взорвать", "бомба",
    "взрывчатк", "оружие массового", "экстремизм", "терроризм", "джихад",
    "политик", "путин", "навальн", "протест", "революция",
    "выборы", "референдум", "спецоперация", "война",
]

_client = None

def _get_client():
    global _client
    if _client is None:
        from config import GIGACHAT_CREDENTIALS
        _client = GigaChat(credentials=GIGACHAT_CREDENTIALS,
                           verify_ssl_certs=False, model="GigaChat-2")
    return _client

def _is_blocked(text):
    low = text.lower()
    return any(w in low for w in BLOCKED_WORDS)

async def generate(story, user_action, arc=1):
    if _is_blocked(user_action):
        return {"text": "🚫 Этот запрос нарушает правила игры. Попробуй другое действие — например, «осматриваюсь».",
                "item": None, "location": None}

    arc_note = ""
    if arc % 20 == 0:
        arc_note = "\n\nВАЖНО: Это ключевой момент сюжета! Сделай крупный поворот: новая локация, важный выбор или встреча с боссом."

    context = f"ПРЕДЫДУЩАЯ ИСТОРИЯ:\n{story}\n\nИГРОК: {user_action}\n\nМАСТЕР:{arc_note}"

    def _sync_call():
        client = _get_client()
        response = client.chat({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            "temperature": 0.7, "max_tokens": 400,
        })
        return response.choices[0].message.content

    loop = asyncio.get_event_loop()
    try:
        text = await asyncio.wait_for(loop.run_in_executor(None, _sync_call), timeout=30.0)
    except asyncio.TimeoutError:
        return {"text": "⏳ Нейросеть не ответила. Попробуй ещё раз.", "item": None, "location": None}
    except Exception as e:
        logging.error(f"GigaChat error: {e}")
        return {"text": "⚠️ Ошибка нейросети. Попробуй позже.", "item": None, "location": None}

    item, location = None, None
    m = re.search(r"\[ITEM:\s*(.+?)\]", text)
    if m:
        item = m.group(1).strip()
        text = re.sub(r"\[ITEM:\s*.+?\]", "", text).strip()
    m = re.search(r"\[LOCATION:\s*(.+?)\]", text)
    if m:
        location = m.group(1).strip()
        text = re.sub(r"\[LOCATION:\s*.+?\]", "", text).strip()

    if _is_blocked(text):
        return {"text": "🚫 Сюжет ушёл в недопустимую тему. Опиши другое действие.", "item": None, "location": None}

    return {"text": text, "item": item, "location": location}
