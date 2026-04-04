import asyncio
import logging
import os
from datetime import datetime, timedelta
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# НАЛАШТУВАННЯ — впиши свої ключі тут
# ============================================================
TELEGRAM_TOKEN = 8602308787:AAFhZMfMNCcTv-yXTDB1mouUFaOBrO_Jac8
TRAVELPAYOUTS_TOKEN = 83ab9d18d7fb0092294828b8104b50a5

# Твій Telegram Chat ID (отримаєш після першого /start)
MY_CHAT_ID = None  # буде збережено автоматично

# Міста вильоту (IATA коди) — додай своє місто
ORIGIN_CITIES = ["KBP", "LWO", "IEV"]  # Київ Бориспіль, Львів, Київ Жуляни

# Максимальна ціна квитка в EUR для алерту
MAX_PRICE_EUR = 100

# Мінімальна знижка від середньої ціни щоб вважатись "deal" (%)
MIN_DISCOUNT_PERCENT = 30

# Скільки топ-deals надсилати щодня
TOP_DEALS_COUNT = 5

# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# Зберігаємо chat_id користувача
chat_id_storage = {}


async def fetch_cheap_flights(origin: str) -> list:
    """Отримати дешеві квитки з Travelpayouts API"""
    deals = []
    
    # Шукаємо на наступні 3 місяці
    date_from = datetime.now() + timedelta(days=7)
    date_to = datetime.now() + timedelta(days=90)
    
    url = "https://api.travelpayouts.com/aviasales/v3/search_by_price_range"
    params = {
        "origin": origin,
        "destination": "-",  # будь-яке направлення
        "value_min": 1,
        "value_max": MAX_PRICE_EUR * 100,  # API повертає в центах
        "one_way": "false",
        "direct": "false",
        "locale": "uk",
        "currency": "eur",
        "market": "ua",
        "limit": 30,
        "page": 1,
        "token": TRAVELPAYOUTS_TOKEN,
        "depart_date": date_from.strftime("%Y-%m"),
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") and data.get("data"):
                        for ticket in data["data"]:
                            price = ticket.get("price", 0) / 100  # конвертуємо з центів
                            deals.append({
                                "origin": ticket.get("origin", origin),
                                "destination": ticket.get("destination", ""),
                                "price": price,
                                "airline": ticket.get("airline", ""),
                                "departure_at": ticket.get("departure_at", ""),
                                "return_at": ticket.get("return_at", ""),
                                "transfers": ticket.get("transfers", 0),
                                "link": f"https://www.aviasales.com{ticket.get('link', '')}",
                            })
    except Exception as e:
        logger.error(f"Помилка при запиті для {origin}: {e}")
    
    return deals


async def fetch_anywhere_deals() -> list:
    """Отримати найдешевші квитки з усіх міст вильоту"""
    all_deals = []
    
    for origin in ORIGIN_CITIES:
        logger.info(f"Шукаємо квитки з {origin}...")
        deals = await fetch_cheap_flights(origin)
        all_deals.extend(deals)
        await asyncio.sleep(1)  # пауза між запитами
    
    # Сортуємо за ціною
    all_deals.sort(key=lambda x: x["price"])
    
    return all_deals[:TOP_DEALS_COUNT * 3]  # беремо з запасом


def format_deal_message(deals: list) -> str:
    """Форматуємо повідомлення з deals"""
    if not deals:
        return "😔 Сьогодні не знайдено особливих deals. Перевіримо завтра!"
    
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"✈️ *НАЙКРАЩІ DEALS* — {now}\n"
    msg += "─" * 30 + "\n\n"
    
    seen_destinations = set()
    count = 0
    
    for deal in deals:
        dest = deal["destination"]
        if dest in seen_destinations:
            continue
        seen_destinations.add(dest)
        
        if count >= TOP_DEALS_COUNT:
            break
        
        # Форматуємо дату
        dep_date = ""
        ret_date = ""
        try:
            dep_dt = datetime.fromisoformat(deal["departure_at"].replace("Z", "+00:00"))
            dep_date = dep_dt.strftime("%d %b")
        except:
            dep_date = deal["departure_at"][:10] if deal["departure_at"] else "?"
            
        try:
            ret_dt = datetime.fromisoformat(deal["return_at"].replace("Z", "+00:00"))
            ret_date = ret_dt.strftime("%d %b")
        except:
            ret_date = deal["return_at"][:10] if deal["return_at"] else "?"
        
        stops = "прямий" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
        price = deal["price"]
        
        # Емодзі ціни
        if price < 30:
            price_emoji = "🔥🔥🔥"
        elif price < 60:
            price_emoji = "🔥🔥"
        elif price < 100:
            price_emoji = "🔥"
        else:
            price_emoji = "💰"
        
        msg += f"{price_emoji} *{deal['origin']} → {dest}*\n"
        msg += f"💶 *€{price:.0f}* туди-назад\n"
        msg += f"📅 {dep_date} — {ret_date} | {stops}\n"
        msg += f"✈️ {deal['airline']}\n"
        msg += f"🔗 [Дивитись на Aviasales]({deal['link']})\n\n"
        
        count += 1
    
    msg += "─" * 30 + "\n"
    msg += "💡 _Ціни змінюються — бронюй швидко!_"
    
    return msg


async def send_daily_deals():
    """Щоденна розсилка deals"""
    logger.info("Запускаємо щоденний пошук deals...")
    
    if not chat_id_storage:
        logger.info("Немає підписників, пропускаємо")
        return
    
    deals = await fetch_anywhere_deals()
    message = format_deal_message(deals)
    
    for chat_id in chat_id_storage.values():
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            logger.info(f"Deals надіслано в чат {chat_id}")
        except Exception as e:
            logger.error(f"Помилка надсилання в {chat_id}: {e}")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обробник команди /start"""
    chat_id_storage["user"] = message.chat.id
    
    await message.answer(
        "👋 *Привіт! Я Flight Deals Bot*\n\n"
        "Щодня о 9:00 я надсилатиму тобі найкращі дешеві квитки "
        "з України куди завгодно по світу! ✈️\n\n"
        "🔍 Шукаю deals з: Київ, Львів\n"
        "💶 Максимальна ціна: до €100\n\n"
        "Команди:\n"
        "/deals — показати deals прямо зараз\n"
        "/help — допомога\n\n"
        "⚡ Перший пошук запускаю зараз...",
        parse_mode="Markdown"
    )
    
    # Одразу показуємо перші deals
    await cmd_deals(message)


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    """Показати deals на запит"""
    chat_id_storage["user"] = message.chat.id
    
    searching_msg = await message.answer("🔍 Шукаю найкращі deals... зачекай 10 секунд")
    
    deals = await fetch_anywhere_deals()
    result = format_deal_message(deals)
    
    await searching_msg.delete()
    await message.answer(result, parse_mode="Markdown", disable_web_page_preview=True)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight Deals Bot — допомога*\n\n"
        "/start — почати / підписатись на щоденні deals\n"
        "/deals — показати deals прямо зараз\n"
        "/help — ця довідка\n\n"
        "🕘 Автоматична розсилка щодня о 9:00\n\n"
        "Шукаю квитки з Києва та Львова куди завгодно "
        "по найнижчих цінах! ✈️",
        parse_mode="Markdown"
    )


async def main():
    # Запускаємо щоденний scheduler о 9:00
    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    scheduler.start()
    
    logger.info("Бот запущено! ✈️")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
