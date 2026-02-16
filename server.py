import os, json, asyncio, base64, hashlib, hmac
from urllib.parse import parse_qsl
from aiohttp import web
import httpx

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# 🔥 КОНФИГ С КЛЮЧОМ ИИ
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL_TEXT as MODEL_TEXT, OPENROUTER_MODEL_VISION as MODEL_VISION

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

SYSTEM_STYLE = (
    "Ты ассистент в стиле 'Огонь + Лёд': спокойный, структурный, "
    "но с яркими акцентами. Пиши по-русски."
)

# ================= BOT =================

@dp.message()
async def on_message(msg: Message):

    # 🔥 КНОПКА ЗАПУСКА WEBAPP
    if msg.text and msg.text.lower() in ("/start", "start"):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔥❄️ Открыть AI",
                        web_app=WebAppInfo(
                            url="https://samarebudit-ops.github.io/tgbot-webapp/"
                        )
                    )
                ]
            ]
        )
        await msg.answer("Открой приложение:", reply_markup=kb)
        return

    if msg.text:
        await msg.answer(f"Напиши /start чтобы открыть AI")

async def _process_update(update_dict: dict):
    update = Update.model_validate(update_dict)
    await dp.feed_update(bot, update)

# ================= WEBHOOK =================

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
