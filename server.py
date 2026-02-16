import os, asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

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

# ---------- WebApp API ----------
async def options_any(request: web.Request):
    return add_cors(web.Response(status=204))

async def api_chat(request: web.Request):
    payload = await request.json()
    text = (payload.get("text") or "").strip()
    resp = web.json_response({"answer": f"✅ Сервер получил: {text}"})
    return add_cors(resp)

async def api_vision(request: web.Request):
    resp = web.json_response({"answer": "✅ Vision endpoint жив (тест)."})
    return add_cors(resp)

async def root(request: web.Request):
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", root)

# Telegram
app.router.add_post("/webhook", webhook)

# WebApp (CORS + endpoints)
app.router.add_options("/api/chat", options_any)
app.router.add_options("/api/vision", options_any)
app.router.add_post("/api/chat", api_chat)
app.router.add_post("/api/vision", api_vision)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
