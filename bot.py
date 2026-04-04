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
# НАЛАШТУВАННЯ
# ============================================================
TELEGRAM_TOKEN = "8602308787:AAFhZMfMNCcTv-yXTDB1mouUFaOBrO_Jac8"
TRAVELPAYOUTS_TOKEN = "83ab9d18d7fb0092294828b8104b50a5"

# Міста вильоту — European cities (бо з України не літають)
# Додай міста звідки плануєш літати
ORIGIN_CITIES = [
    "WAW",  # Варшава
    "KRK",  # Краків
    "RZE",  # Жешув (найближче до кордону)
    "LUZ",  # Люблін
    "BUD",  # Будапешт
    "PRG",  # Прага
]

MAX_PRICE_EUR = 150       # максимальна ціна для пошуку
TOP_DEALS_COUNT = 5       # скільки deals показувати по кожному типу

# Середні ціни по напрямках (для розрахунку знижки)
# Якщо напрямок невідомий — використовуємо середнє по всіх
AVERAGE_PRICES = {
    "default_oneway": 120,   # середній one-way в Європі
    "default_return": 200,   # середній return в Європі
}

# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

chat_id_storage = {}

# Кеш середніх цін щоб не рахувати кожен раз
price_cache = {}


async def fetch_oneway_deals() -> list:
    """Пошук one-way квитків — звідусіль куди завгодно"""
    all_deals = []

    date_from = datetime.now() + timedelta(days=7)

    for origin in ORIGIN_CITIES:
        url = "https://api.travelpayouts.com/aviasales/v3/search_by_price_range"
        params = {
            "origin": origin,
            "destination": "-",
            "value_min": 1,
            "value_max": MAX_PRICE_EUR * 100,
            "one_way": "true",
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
                            for t in data["data"]:
                                price = t.get("price", 0) / 100
                                all_deals.append({
                                    "type": "oneway",
                                    "origin": t.get("origin", origin),
                                    "destination": t.get("destination", ""),
                                    "price": price,
                                    "airline": t.get("airline", ""),
                                    "departure_at": t.get("departure_at", ""),
                                    "return_at": None,
                                    "transfers": t.get("transfers", 0),
                                    "link": f"https://www.aviasales.com{t.get('link', '')}",
                                })
        except Exception as e:
            logger.error(f"One-way помилка {origin}: {e}")

        await asyncio.sleep(0.5)

    all_deals.sort(key=lambda x: x["price"])
    return all_deals


async def fetch_return_deals() -> list:
    """Пошук туди-назад до 7 днів"""
    all_deals = []

    date_from = datetime.now() + timedelta(days=7)

    for origin in ORIGIN_CITIES:
        url = "https://api.travelpayouts.com/aviasales/v3/search_by_price_range"
        params = {
            "origin": origin,
            "destination": "-",
            "value_min": 1,
            "value_max": MAX_PRICE_EUR * 100,
            "one_way": "false",
            "direct": "false",
            "locale": "uk",
            "currency": "eur",
            "market": "ua",
            "limit": 30,
            "page": 1,
            "token": TRAVELPAYOUTS_TOKEN,
            "depart_date": date_from.strftime("%Y-%m"),
            "nights_in_dst_from": 1,
            "nights_in_dst_to": 7,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("success") and data.get("data"):
                            for t in data["data"]:
                                price = t.get("price", 0) / 100

                                # Рахуємо кількість ночей
                                nights = None
                                try:
                                    dep = datetime.fromisoformat(t["departure_at"].replace("Z", "+00:00"))
                                    ret = datetime.fromisoformat(t["return_at"].replace("Z", "+00:00"))
                                    nights = (ret - dep).days
                                except:
                                    pass

                                if nights is not None and nights > 7:
                                    continue  # пропускаємо більше 7 ночей

                                all_deals.append({
                                    "type": "return",
                                    "origin": t.get("origin", origin),
                                    "destination": t.get("destination", ""),
                                    "price": price,
                                    "airline": t.get("airline", ""),
                                    "departure_at": t.get("departure_at", ""),
                                    "return_at": t.get("return_at", ""),
                                    "transfers": t.get("transfers", 0),
                                    "nights": nights,
                                    "link": f"https://www.aviasales.com{t.get('link', '')}",
                                })
        except Exception as e:
            logger.error(f"Return помилка {origin}: {e}")

        await asyncio.sleep(0.5)

    all_deals.sort(key=lambda x: x["price"])
    return all_deals


def calc_discount(price: float, trip_type: str, destination: str) -> tuple:
    """Розрахувати середню ціну і % знижки"""
    key = f"{trip_type}_{destination}"

    if key in price_cache:
        avg = price_cache[key]
    else:
        # Використовуємо дефолтні середні ціни
        if trip_type == "oneway":
            avg = AVERAGE_PRICES["default_oneway"]
        else:
            avg = AVERAGE_PRICES["default_return"]

    if avg > 0 and price < avg:
        discount = round((avg - price) / avg * 100)
    else:
        discount = 0

    return avg, discount


def format_date(date_str: str) -> str:
    if not date_str:
        return "?"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        months = ["січ", "лют", "бер", "квіт", "трав", "черв",
                  "лип", "серп", "вер", "жовт", "лист", "груд"]
        return f"{dt.day} {months[dt.month-1]}"
    except:
        return date_str[:10]


def format_deals_message(oneway_deals: list, return_deals: list) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"✈️ *FLIGHT DEALS* — {now}\n\n"

    # ── ВАРІАНТ 1: ONE-WAY ──
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🛫 *ВАРІАНТ 1 — В ОДИН БІК*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if oneway_deals:
        seen = set()
        count = 0
        for deal in oneway_deals:
            key = f"{deal['origin']}-{deal['destination']}"
            if key in seen:
                continue
            seen.add(key)
            if count >= TOP_DEALS_COUNT:
                break

            avg, discount = calc_discount(deal["price"], "oneway", deal["destination"])
            dep_date = format_date(deal["departure_at"])
            stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"

            if discount >= 40:
                fire = "🔥🔥🔥"
            elif discount >= 20:
                fire = "🔥🔥"
            elif discount > 0:
                fire = "🔥"
            else:
                fire = "💰"

            msg += f"{fire} *{deal['origin']} → {deal['destination']}*\n"
            msg += f"💶 *€{deal['price']:.0f}* "
            if discount > 0:
                msg += f"_(середня ~€{avg:.0f}, дешевше на {discount}%)_\n"
            else:
                msg += f"_(середня ~€{avg:.0f})_\n"
            msg += f"📅 {dep_date} | {stops} | {deal['airline']}\n"
            msg += f"🔗 [Дивитись]({deal['link']})\n\n"
            count += 1
    else:
        msg += "😔 Deals не знайдено\n\n"

    # ── ВАРІАНТ 2: ТУДИ-НАЗАД ──
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🔄 *ВАРІАНТ 2 — ТУДИ І НАЗАД (до 7 ночей)*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if return_deals:
        seen = set()
        count = 0
        for deal in return_deals:
            key = f"{deal['origin']}-{deal['destination']}"
            if key in seen:
                continue
            seen.add(key)
            if count >= TOP_DEALS_COUNT:
                break

            avg, discount = calc_discount(deal["price"], "return", deal["destination"])
            dep_date = format_date(deal["departure_at"])
            ret_date = format_date(deal.get("return_at", ""))
            nights_str = f"{deal['nights']} н." if deal.get("nights") else ""
            stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"

            if discount >= 40:
                fire = "🔥🔥🔥"
            elif discount >= 20:
                fire = "🔥🔥"
            elif discount > 0:
                fire = "🔥"
            else:
                fire = "💰"

            msg += f"{fire} *{deal['origin']} → {deal['destination']}*\n"
            msg += f"💶 *€{deal['price']:.0f}* туди-назад "
            if discount > 0:
                msg += f"_(середня ~€{avg:.0f}, дешевше на {discount}%)_\n"
            else:
                msg += f"_(середня ~€{avg:.0f})_\n"
            msg += f"📅 {dep_date} — {ret_date}"
            if nights_str:
                msg += f" ({nights_str})"
            msg += f" | {stops} | {deal['airline']}\n"
            msg += f"🔗 [Дивитись]({deal['link']})\n\n"
            count += 1
    else:
        msg += "😔 Deals не знайдено\n\n"

    msg += "💡 _Ціни змінюються — бронюй швидко!_"
    return msg


async def search_and_send(chat_id: int):
    """Шукаємо і надсилаємо deals"""
    oneway = await fetch_oneway_deals()
    ret = await fetch_return_deals()
    message = format_deals_message(oneway, ret)
    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )


async def send_daily_deals():
    logger.info("Щоденний пошук deals...")
    for chat_id in chat_id_storage.values():
        try:
            await search_and_send(chat_id)
        except Exception as e:
            logger.error(f"Помилка надсилання: {e}")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id_storage["user"] = message.chat.id
    await message.answer(
        "👋 *Привіт! Я Flight Deals Bot*\n\n"
        "Шукаю дешеві квитки з Польщі, Угорщини, Чехії — "
        "куди завгодно по світу! ✈️\n\n"
        "📍 Міста вильоту: Варшава, Краків, Жешув, Люблін, Будапешт, Прага\n"
        "💶 До €150\n\n"
        "🛫 *Варіант 1* — в один бік\n"
        "🔄 *Варіант 2* — туди-назад до 7 ночей\n\n"
        "Для кожного квитка показую середню ціну і % знижки!\n\n"
        "⚡ Запускаю пошук...",
        parse_mode="Markdown"
    )
    searching = await message.answer("🔍 Шукаю deals... зачекай 20-30 секунд")
    await search_and_send(message.chat.id)
    await searching.delete()


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    chat_id_storage["user"] = message.chat.id
    searching = await message.answer("🔍 Шукаю deals... зачекай 20-30 секунд")
    await search_and_send(message.chat.id)
    await searching.delete()


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight Deals Bot*\n\n"
        "/start — підписатись\n"
        "/deals — deals прямо зараз\n"
        "/help — довідка\n\n"
        "🕘 Автоматично щодня о 9:00\n\n"
        "Шукаю з: Варшава, Краків, Жешув, Люблін, Будапешт, Прага\n"
        "Показую два варіанти:\n"
        "🛫 В один бік\n"
        "🔄 Туди-назад до 7 ночей\n"
        "📊 З розрахунком знижки від середньої ціни",
        parse_mode="Markdown"
    )


async def main():
    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    scheduler.start()
    logger.info("Бот запущено! ✈️")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
