import os, json, asyncio, base64, hashlib, hmac
from urllib.parse import parse_qsl
from aiohttp import web
import httpx

from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_TEXT = os.getenv("OPENROUTER_MODEL_TEXT", "x-ai/grok-2")
MODEL_VISION = os.getenv("OPENROUTER_MODEL_VISION", MODEL_TEXT)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

SYSTEM_STYLE = (
    "Ты ассистент в стиле 'Огонь + Лёд': структурно, спокойно, но с яркими короткими акцентами. "
    "Пиши по-русски, по делу."
)

# --- Telegram WebApp auth (initData verification) ---
def _tg_check_hash(init_data: str) -> bool:
    """
    Verify Telegram WebApp initData.
    Docs: https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
    """
    if not init_data:
        return False
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    recv_hash = pairs.pop("hash", "")
    if not recv_hash:
        return False

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc_hash, recv_hash)

async def _openrouter(messages, model: str) -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ На сервере не задан OPENROUTER_API_KEY (Render → Environment)."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/Finansistic_bot",
        "X-Title": "FinansisticBot"
    }
    payload = {"model": model, "messages": messages, "temperature": 0.7}

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"].strip()

# --- Bot (still works in chat) ---
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

# --- Webhook endpoint for Telegram ---
async def webhook(request: web.Request):
    data = await request.json()
    asyncio.create_task(_process_update(data))
    return web.Response(text="ok")

# --- CORS helper ---
def _cors(resp: web.StreamResponse) -> web.StreamResponse:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return resp

async def options(_):
    return _cors(web.Response(text="ok"))

# --- API for WebApp ---
async def api_chat(request: web.Request):
    body = await request.json()
    init_data = body.get("initData", "")
    text = (body.get("text") or "").strip()

    if not _tg_check_hash(init_data):
        return _cors(web.json_response({"ok": False, "error": "initData invalid"}, status=401))
    if not text:
        return _cors(web.json_response({"ok": False, "error": "empty text"}, status=400))

    messages = [
        {"role": "system", "content": SYSTEM_STYLE},
        {"role": "user", "content": text},
    ]
    try:
        answer = await _openrouter(messages, MODEL_TEXT)
    except Exception as e:
        answer = f"⚠️ Ошибка ИИ: {e}"

    return _cors(web.json_response({"ok": True, "answer": answer}))

async def api_vision(request: web.Request):
    body = await request.json()
    init_data = body.get("initData", "")
    prompt = (body.get("prompt") or "Что на изображении? Опиши кратко и сделай вывод.").strip()
    data_url = body.get("imageDataUrl", "")

    if not _tg_check_hash(init_data):
        return _cors(web.json_response({"ok": False, "error": "initData invalid"}, status=401))
    if not data_url.startswith("data:image/"):
        return _cors(web.json_response({"ok": False, "error": "imageDataUrl required"}, status=400))

    # data:image/jpeg;base64,....
    try:
        b64 = data_url.split(",", 1)[1]
        # quick sanity check
        base64.b64decode(b64[:100] + "==")
    except Exception:
        return _cors(web.json_response({"ok": False, "error": "bad imageDataUrl"}, status=400))

    messages = [
        {"role": "system", "content": SYSTEM_STYLE},
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]},
    ]
    try:
        answer = await _openrouter(messages, MODEL_VISION)
    except Exception as e:
        answer = f"⚠️ Ошибка Vision: {e}"

    return _cors(web.json_response({"ok": True, "answer": answer}))

app = web.Application()
app.router.add_get("/", lambda r: web.Response(text="ok"))
app.router.add_post("/webhook", webhook)

# WebApp API (+ preflight)
app.router.add_route("OPTIONS", "/api/chat", options)
app.router.add_route("OPTIONS", "/api/vision", options)
app.router.add_post("/api/chat", api_chat)
app.router.add_post("/api/vision", api_vision)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)
