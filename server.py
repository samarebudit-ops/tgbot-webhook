import os
import json
import asyncio
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.types import Update

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.update()
async def handle_update(update: Update):
    if not update.message:
        return
    msg = update.message

    if msg.web_app_data:
        raw = msg.web_app_data.data
        await bot.send_message(msg.chat.id, f"✅ WebApp data:\n{raw}")
        return

    if msg.text:
        await bot.send_message(msg.chat.id, f"Эхо: {msg.text}")

async def process_update(update_data):
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)

async def webhook(request: web.Request):
    data = await request.json()

    # 🔥 ОТВЕЧАЕМ СРАЗУ
    asyncio.create_task(process_update(data))

    return web.Response(text="ok")

async def health(request: web.Request):
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", health)
app.router.add_post("/webhook", webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)
