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

    # WebApp data
    if msg.web_app_data:
        raw = msg.web_app_data.data
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}
        await bot.send_message(msg.chat.id, f"✅ WebApp data:\n{payload}")
        return

    # обычный текст
    if msg.text:
        await bot.send_message(msg.chat.id, f"Эхо: {msg.text}")

async def webhook(request: web.Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return web.Response(text="ok")

async def health(request: web.Request):
    return web.Response(text="ok")

app = web.Application()
app.router.add_get("/", health)
app.router.add_post("/webhook", webhook)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)
