import os
import json
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message()
async def on_message(msg: Message):
    if msg.web_app_data:
        await msg.answer(f"📦 WebApp: {msg.web_app_data.data}")
        return

    if msg.text:
        await msg.answer(f"✅ Render webhook жив. Ты написал: {msg.text}")

async def _process_update(update_dict: dict):
    update = Update.model_validate(update_dict)
    await dp.feed_update(bot, update)

async def webhook(request: web.Request):
    data = await request.json()
    # отвечаем Telegram сразу, обработку делаем в фоне
    asyncio.create_task(_process_update(data))
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", lambda r: web.Response(text="ok"))
app.router.add_post("/webhook", webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
