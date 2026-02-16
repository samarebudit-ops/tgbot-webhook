import os, asyncio
from aiohttp import web
import httpx

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import (
    DEFAULT_PROVIDER,
    OPENROUTER_API_KEY, OPENROUTER_MODEL_TEXT, OPENROUTER_MODEL_VISION,
    GROQ_API_KEY, GROQ_MODEL_TEXT
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = "https://samarebudit-ops.github.io/tgbot-webapp/"
ALLOWED_ORIGIN = "https://samarebudit-ops.github.io"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

def add_cors(resp: web.StreamResponse):
    resp.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp

@dp.message()
async def on_message(msg: Message):
    if msg.text and msg.text.lower() in ("/start", "start"):
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🔥❄️ Открыть AI",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]])
        await msg.answer("Нажми кнопку, чтобы запустить WebApp:", reply_markup=kb)
        return
    await msg.answer("Напиши /start ✅")

async def _process_update(update_dict: dict):
    update = Update.model_validate(update_dict)
    await dp.feed_update(bot, update)

# ---------- Telegram webhook ----------
async def webhook(request: web.Request):
    data = await request.json()
    asyncio.create_task(_process_update(data))
    return web.Response(text="ok")

# ---------- LLM clients ----------
async def call_openrouter_text(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ OPENROUTER_API_KEY не задан"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL_TEXT,
        "messages": [
            {"role": "system", "content": "Стиль: Огонь+Лёд. Отвечай по-русски, структурно."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return (j["choices"][0]["message"]["content"] or "").strip()

async def call_groq_text(prompt: str) -> str:
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY не задан"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL_TEXT,
        "messages": [
            {"role": "system", "content": "Стиль: Огонь+Лёд. Отвечай по-русски, структурно."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return (j["choices"][0]["message"]["content"] or "").strip()

async def call_openrouter_vision(image_data_url: str, prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ OPENROUTER_API_KEY не задан"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    # image_data_url выглядит как "data:image/png;base64,...."
    payload = {
        "model": OPENROUTER_MODEL_VISION,
        "messages": [
            {"role": "system", "content": "Стиль: Огонь+Лёд. Отвечай по-русски, кратко и по делу."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]},
        ],
        "temperature": 0.4,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return (j["choices"][0]["message"]["content"] or "").strip()

# ---------- WebApp API ----------
async def options_any(request: web.Request):
    return add_cors(web.Response(status=204))

async def api_chat(request: web.Request):
    payload = await request.json()
    text = (payload.get("text") or "").strip()
    provider = (payload.get("provider") or DEFAULT_PROVIDER or "openrouter").lower()

    if not text:
        resp = web.json_response({"answer": "⚠️ Пустой текст"})
        return add_cors(resp)

    try:
        if provider == "groq":
            answer = await call_groq_text(text)
        else:
            answer = await call_openrouter_text(text)
        resp = web.json_response({"answer": answer, "provider": provider})
        return add_cors(resp)
    except httpx.HTTPError as e:
        resp = web.json_response({"answer": f"⚠️ Ошибка запроса: {str(e)}"})
        return add_cors(resp)

async def api_vision(request: web.Request):
    payload = await request.json()
    image_data_url = payload.get("imageDataUrl") or ""
    prompt = (payload.get("prompt") or "Опиши, что на изображении.").strip()

    if not image_data_url.startswith("data:image/"):
        resp = web.json_response({"answer": "⚠️ Нужен imageDataUrl (data:image/...base64)"})
        return add_cors(resp)

    try:
        answer = await call_openrouter_vision(image_data_url, prompt)
        resp = web.json_response({"answer": answer})
        return add_cors(resp)
    except httpx.HTTPError as e:
        resp = web.json_response({"answer": f"⚠️ Ошибка vision: {str(e)}"})
        return add_cors(resp)

async def root(request: web.Request):
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", root)
app.router.add_post("/webhook", webhook)

app.router.add_options("/api/chat", options_any)
app.router.add_options("/api/vision", options_any)
app.router.add_post("/api/chat", api_chat)
app.router.add_post("/api/vision", api_vision)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
