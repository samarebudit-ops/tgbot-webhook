import os, asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = "https://samarebudit-ops.github.io/tgbot-webapp/"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

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

    await msg.answer("Напиши /start — дам кнопку запуска WebApp ✅")

async def _process_update(update_dict: dict):
    update = Update.model_validate(update_dict)
    await dp.feed_update(bot, update)

async def webhook(request: web.Request):
    data = await request.json()
    asyncio.create_task(_process_update(data))
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", lambda r: web.Response(text="ok"))
app.router.add_post("/webhook", webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
