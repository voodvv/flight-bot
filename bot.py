import asyncio
import logging
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

MAX_PRICE_EUR = 150
TOP_DEALS_COUNT = 5

ORIGIN_CITIES = [
    # Найближчі до України
    "WAW", "KRK", "RZE", "WRO", "GDN", "KTW", "POZ",
    "BUD", "PRG", "BTS", "KSC",
    "OTP", "CLJ", "TSR",
    # Великі хаби (тут завжди є дані в кеші)
    "VIE", "ZRH", "MUC", "FRA", "BER", "HAM", "STR", "DUS",
    "CDG", "ORY", "LYS", "NCE", "BOD",
    "LHR", "LGW", "STN", "MAN", "EDI", "BRS",
    "AMS", "BRU", "LUX",
    "FCO", "MXP", "VCE", "NAP", "BLQ",
    "MAD", "BCN", "AGP", "VLC", "PMI",
    "LIS", "OPO",
    "ATH", "SKG",
    "CPH", "ARN", "OSL", "HEL",
    "RIX", "TLL", "VNO",
    "DUB",
    "SOF", "BEG", "ZAG",
    "IST", "SAW",
    "LCA",
]

AVERAGE_PRICES = {"oneway": 110, "return": 185}

# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
chat_id_storage = {}


async def fetch_cheapest_from(session: aiohttp.ClientSession, origin: str, one_way: bool) -> list:
    results = []
    now = datetime.now()

    for i in range(1, 4):  # наступні 3 місяці
        month = (now + timedelta(days=30 * i)).strftime("%Y-%m")

        params = {
            "origin": origin,
            "depart_date": month,
            "currency": "eur",
            "token": TRAVELPAYOUTS_TOKEN,
            "one_way": "true" if one_way else "false",
        }
        if not one_way:
            ret_month = (now + timedelta(days=30 * i + 5)).strftime("%Y-%m")
            params["return_date"] = ret_month

        try:
            async with session.get(
                "https://api.travelpayouts.com/v1/prices/cheap",
                params=params,
                headers={"x-access-token": TRAVELPAYOUTS_TOKEN},
                timeout=aiohttp.ClientTimeout(total=12)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") and data.get("data"):
                        for dest, tickets in data["data"].items():
                            for _, t in tickets.items():
                                price = t.get("price", 0)
                                if price <= 0 or price > MAX_PRICE_EUR:
                                    continue

                                nights = None
                                if not one_way:
                                    try:
                                        dep = datetime.fromisoformat(t["departure_at"].replace("Z", "+00:00"))
                                        ret_dt = datetime.fromisoformat(t["return_at"].replace("Z", "+00:00"))
                                        nights = (ret_dt - dep).days
                                        if nights > 7 or nights < 1:
                                            continue
                                    except:
                                        pass

                                results.append({
                                    "origin": origin,
                                    "destination": dest,
                                    "price": price,
                                    "airline": t.get("airline", ""),
                                    "departure_at": t.get("departure_at", ""),
                                    "return_at": t.get("return_at", "") if not one_way else None,
                                    "transfers": t.get("transfers", 0),
                                    "nights": nights,
                                    "link": f"https://www.aviasales.com/search/{origin}{dest}",
                                })
        except Exception as e:
            logger.warning(f"{origin}: {e}")

    return results


async def fetch_all_deals(one_way: bool) -> list:
    all_deals = []
    connector = aiohttp.TCPConnector(limit=10)

    async with aiohttp.ClientSession(connector=connector) as session:
        batch_size = 8
        for i in range(0, len(ORIGIN_CITIES), batch_size):
            batch = ORIGIN_CITIES[i:i + batch_size]
            tasks = [fetch_cheapest_from(session, o, one_way) for o in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_deals.extend(r)
            await asyncio.sleep(0.5)

    # Дедуплікація + сортування
    seen = set()
    unique = []
    for d in sorted(all_deals, key=lambda x: x["price"]):
        key = f"{d['origin']}-{d['destination']}"
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique


def calc_discount(price: float, trip_type: str) -> tuple:
    avg = AVERAGE_PRICES.get(trip_type, 150)
    discount = round((avg - price) / avg * 100) if price < avg else 0
    return avg, discount


def format_date(date_str: str) -> str:
    if not date_str:
        return "?"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        m = ["січ","лют","бер","квіт","трав","черв","лип","серп","вер","жовт","лист","груд"]
        return f"{dt.day} {m[dt.month-1]}"
    except:
        return date_str[:7]


def format_section(deals: list, one_way: bool) -> str:
    trip_type = "oneway" if one_way else "return"

    if one_way:
        msg = "━━━━━━━━━━━━━━━━━━━━\n🛫 *ВАРІАНТ 1 — В ОДИН БІК*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        msg = "━━━━━━━━━━━━━━━━━━━━\n🔄 *ВАРІАНТ 2 — ТУДИ І НАЗАД (до 7 ночей)*\n━━━━━━━━━━━━━━━━━━━━\n\n"

    if not deals:
        return msg + "😔 Немає даних у кеші — спробуй пізніше або завтра вранці\n\n"

    count = 0
    for deal in deals:
        if count >= TOP_DEALS_COUNT:
            break

        avg, discount = calc_discount(deal["price"], trip_type)
        dep_date = format_date(deal["departure_at"])
        stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
        fire = "🔥🔥🔥" if discount >= 40 else "🔥🔥" if discount >= 20 else "🔥" if discount > 0 else "💰"

        msg += f"{fire} *{deal['origin']} → {deal['destination']}*\n"
        msg += f"💶 *€{deal['price']:.0f}*"
        if not one_way:
            msg += " туди-назад"
        msg += "\n"
        if discount > 0:
            msg += f"📊 ~€{avg} середня | дешевше на *{discount}%*\n"
        else:
            msg += f"📊 ~€{avg} середня ціна\n"

        msg += f"📅 {dep_date}"
        if not one_way and deal.get("return_at"):
            ret_date = format_date(deal["return_at"])
            nights_str = f" · {deal['nights']} н." if deal.get("nights") else ""
            msg += f" — {ret_date}{nights_str}"
        msg += f" | {stops}"
        if deal["airline"]:
            msg += f" | {deal['airline']}"
        msg += f"\n🔗 [Дивитись на Aviasales]({deal['link']})\n\n"
        count += 1

    return msg


async def do_search() -> str:
    oneway_deals, return_deals = await asyncio.gather(
        fetch_all_deals(one_way=True),
        fetch_all_deals(one_way=False)
    )
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"✈️ *FLIGHT DEALS* — {now}\n"
    msg += f"🌍 Пошук по {len(ORIGIN_CITIES)} аеропортах Європи\n\n"
    msg += format_section(oneway_deals, one_way=True)
    msg += format_section(return_deals, one_way=False)
    msg += "💡 _Ціни з кешу Aviasales — бронюй швидко!_"
    return msg


async def send_daily_deals():
    logger.info("Щоденний пошук...")
    for chat_id in chat_id_storage.values():
        try:
            msg = await do_search()
            await bot.send_message(chat_id, msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Помилка: {e}")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id_storage["user"] = message.chat.id
    await message.answer(
        "👋 *Привіт! Я Flight Deals Bot*\n\n"
        f"Шукаю дешеві квитки по *{len(ORIGIN_CITIES)} аеропортах Європи*\n\n"
        "🛫 В один бік\n🔄 Туди-назад до 7 ночей\n📊 З % знижки\n\n"
        "⚡ Запускаю пошук (~30 сек)...",
        parse_mode="Markdown"
    )
    wait = await message.answer("🔍 Шукаю deals...")
    msg = await do_search()
    await wait.delete()
    await message.answer(msg, parse_mode="Markdown", disable_web_page_preview=True)


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    chat_id_storage["user"] = message.chat.id
    wait = await message.answer("🔍 Шукаю deals (~30 сек)...")
    msg = await do_search()
    await wait.delete()
    await message.answer(msg, parse_mode="Markdown", disable_web_page_preview=True)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight Deals Bot*\n\n"
        "/start — підписатись\n/deals — deals прямо зараз\n/help — довідка\n\n"
        f"🌍 {len(ORIGIN_CITIES)} аеропортів Європи\n🕘 Авто о 9:00",
        parse_mode="Markdown"
    )


async def main():
    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    scheduler.start()
    logger.info(f"Бот запущено! ✈️")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
