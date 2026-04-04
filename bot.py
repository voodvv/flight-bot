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

# ============================================================
# УСІ АЕРОПОРТИ ЄВРОПИ + НАЙБЛИЖЧІ ДО УКРАЇНИ
# Розділені по пріоритету — найближчі йдуть першими
# ============================================================
ORIGIN_CITIES = [
    # ── НАЙБЛИЖЧІ ДО УКРАЇНИ (пріоритет) ──
    "RZE",  # Жешув, Польща (найближчий до кордону)
    "LUZ",  # Люблін, Польща
    "KRK",  # Краків, Польща
    "WAW",  # Варшава, Польща
    "WRO",  # Вроцлав, Польща
    "GDN",  # Гданськ, Польща
    "POZ",  # Познань, Польща
    "KTW",  # Катовіце, Польща
    "SZZ",  # Щецин, Польща
    "BUD",  # Будапешт, Угорщина
    "DEB",  # Дебрецен, Угорщина
    "BRQ",  # Брно, Чехія
    "PRG",  # Прага, Чехія
    "KSC",  # Кошіце, Словаччина
    "BTS",  # Братислава, Словаччина
    "CLJ",  # Клуж-Напока, Румунія
    "SUJ",  # Сату-Маре, Румунія
    "OMR",  # Орадя, Румунія
    "TSR",  # Тімішоара, Румунія
    "OTP",  # Бухарест, Румунія
    "SBZ",  # Сібіу, Румунія
    "IAS",  # Яси, Румунія
    "BCM",  # Бакеу, Румунія
    "LJU",  # Любляна, Словенія
    "ZAG",  # Загреб, Хорватія
    "OSI",  # Осієк, Хорватія
    "BEG",  # Белград, Сербія
    "INI",  # Ніш, Сербія
    "SKP",  # Скоп'є, Північна Македонія
    "SOF",  # Софія, Болгарія
    "PDV",  # Пловдів, Болгарія
    "VAR",  # Варна, Болгарія
    "BOJ",  # Бургас, Болгарія
    "TGD",  # Подгориця, Чорногорія
    "TIV",  # Тіват, Чорногорія
    "TIA",  # Тирана, Албанія
    "OHD",  # Охрид, Північна Македонія
    "MDU",  # Кишинів, Молдова

    # ── ЦЕНТРАЛЬНА ЄВРОПА ──
    "VIE",  # Відень, Австрія
    "GRZ",  # Грац, Австрія
    "INN",  # Інсбрук, Австрія
    "KLU",  # Клагенфурт, Австрія
    "SZG",  # Зальцбург, Австрія
    "ZRH",  # Цюрих, Швейцарія
    "GVA",  # Женева, Швейцарія
    "BSL",  # Базель, Швейцарія
    "BRN",  # Берн, Швейцарія
    "MUC",  # Мюнхен, Німеччина
    "FRA",  # Франкфурт, Німеччина
    "BER",  # Берлін, Німеччина
    "DUS",  # Дюссельдорф, Німеччина
    "HAM",  # Гамбург, Німеччина
    "STR",  # Штутгарт, Німеччина
    "CGN",  # Кельн, Німеччина
    "HAJ",  # Ганновер, Німеччина
    "NUE",  # Нюрнберг, Німеччина
    "LEJ",  # Лейпциг, Німеччина
    "DRS",  # Дрезден, Німеччина
    "BRE",  # Бремен, Німеччина
    "FDH",  # Фрідріхсгафен, Німеччина
    "PAD",  # Падерборн, Німеччина
    "ERF",  # Ерфурт, Німеччина
    "SCN",  # Саарбрюккен, Німеччина
    "FMM",  # Меммінген, Німеччина
    "HHN",  # Хан (Франкфурт Хан), Німеччина
    "NRN",  # Вайзе/Дюссельдорф Вест, Німеччина
    "DTM",  # Дортмунд, Німеччина
    "RLG",  # Росток, Німеччина

    # ── ЗАХІДНА ЄВРОПА ──
    "CDG",  # Париж Шарль де Голль, Франція
    "ORY",  # Париж Орлі, Франція
    "LYS",  # Ліон, Франція
    "MRS",  # Марсель, Франція
    "NCE",  # Ніцца, Франція
    "TLS",  # Тулуза, Франція
    "BOD",  # Бордо, Франція
    "NTE",  # Нант, Франція
    "LIL",  # Лілль, Франція
    "SXB",  # Страсбург, Франція
    "BES",  # Брест, Франція
    "MPL",  # Монпельє, Франція
    "BIA",  # Бастія, Корсика
    "AJA",  # Аяччо, Корсика
    "LHR",  # Лондон Хітроу, Велика Британія
    "LGW",  # Лондон Гетвік, Велика Британія
    "STN",  # Лондон Станстед, Велика Британія
    "LTN",  # Лондон Лутон, Велика Британія
    "LCY",  # Лондон Сіті, Велика Британія
    "MAN",  # Манчестер, Велика Британія
    "BHX",  # Бірмінгем, Велика Британія
    "EDI",  # Единбург, Велика Британія
    "GLA",  # Глазго, Велика Британія
    "BRS",  # Брістоль, Велика Британія
    "NCL",  # Ньюкасл, Велика Британія
    "LPL",  # Ліверпуль, Велика Британія
    "EMA",  # Іст-Мідлендс, Велика Британія
    "ABZ",  # Абердін, Велика Британія
    "BFS",  # Белфаст, Велика Британія
    "DUB",  # Дублін, Ірландія
    "SNN",  # Шеннон, Ірландія
    "ORK",  # Корк, Ірландія
    "NOC",  # Ноккі, Ірландія
    "AMS",  # Амстердам, Нідерланди
    "EIN",  # Ейндговен, Нідерланди
    "RTM",  # Роттердам, Нідерланди
    "GRQ",  # Гронінген, Нідерланди
    "BRU",  # Брюссель, Бельгія
    "CRL",  # Брюссель Шарлеруа, Бельгія
    "LGG",  # Льєж, Бельгія
    "LUX",  # Люксембург
    "LIS",  # Лісабон, Португалія
    "OPO",  # Порту, Португалія
    "FAO",  # Фару, Португалія
    "FNC",  # Фуншал (Мадейра), Португалія
    "PDL",  # Понта-Делгада (Азори), Португалія
    "MAD",  # Мадрид, Іспанія
    "BCN",  # Барселона, Іспанія
    "AGP",  # Малага, Іспанія
    "ALC",  # Аліканте, Іспанія
    "PMI",  # Пальма де Майорка, Іспанія
    "IBZ",  # Ібіца, Іспанія
    "VLC",  # Валенсія, Іспанія
    "SVQ",  # Севілья, Іспанія
    "BIO",  # Більбао, Іспанія
    "SDR",  # Сантандер, Іспанія
    "SCQ",  # Сантьяго де Компостела, Іспанія
    "OVD",  # Ов'єдо, Іспанія
    "VGO",  # Віго, Іспанія
    "GRX",  # Гранада, Іспанія
    "MHN",  # Менорка, Іспанія
    "ACE",  # Ланзароте, Канарські о-ви
    "TFS",  # Тенеріфе Південь, Канарські о-ви
    "TFN",  # Тенеріфе Північ, Канарські о-ви
    "LPA",  # Лас-Пальмас (Гран Канарія), Канарські о-ви
    "FUE",  # Фуертевентура, Канарські о-ви
    "GMZ",  # Ла Гомера, Канарські о-ви

    # ── ПІВНІЧНА ЄВРОПА ──
    "CPH",  # Копенгаген, Данія
    "AAL",  # Ольборг, Данія
    "BLL",  # Більунд, Данія
    "ARN",  # Стокгольм Арланда, Швеція
    "NYO",  # Стокгольм Скавста, Швеція
    "GOT",  # Гетеборг, Швеція
    "MMX",  # Мальме, Швеція
    "OSL",  # Осло, Норвегія
    "TRF",  # Осло Торп, Норвегія
    "BGO",  # Берген, Норвегія
    "SVG",  # Ставангер, Норвегія
    "TRD",  # Тронгейм, Норвегія
    "HEL",  # Гельсінкі, Фінляндія
    "TMP",  # Тампере, Фінляндія
    "TKU",  # Турку, Фінляндія
    "OUL",  # Оулу, Фінляндія
    "RVN",  # Рованіємі, Фінляндія
    "KEF",  # Рейк'явік, Ісландія
    "RKV",  # Рейк'явік внутрішній, Ісландія

    # ── БАЛТІЙСЬКІ КРАЇНИ ──
    "RIX",  # Рига, Латвія
    "TLL",  # Таллін, Естонія
    "VNO",  # Вільнюс, Литва
    "KUN",  # Каунас, Литва
    "PLQ",  # Паланга, Литва

    # ── СЕРЕДЗЕМНОМОР'Я ──
    "FCO",  # Рим Фьюмічино, Італія
    "CIA",  # Рим Чампіно, Італія
    "MXP",  # Мілан Мальпенса, Італія
    "LIN",  # Мілан Лінате, Італія
    "BGY",  # Мілан Бергамо, Італія
    "VCE",  # Венеція, Італія
    "TSF",  # Тревізо, Італія
    "NAP",  # Неаполь, Італія
    "BRI",  # Барі, Італія
    "PSR",  # Пескара, Італія
    "CAG",  # Кальярі, Сардинія
    "AHO",  # Алгеро, Сардинія
    "OLB",  # Ольбія, Сардинія
    "CTA",  # Катанія, Сицилія
    "PMO",  # Палермо, Сицилія
    "TRS",  # Трієст, Італія
    "VRN",  # Верона, Італія
    "BLQ",  # Болонья, Італія
    "FLR",  # Флоренція, Італія
    "PSA",  # Піза, Італія
    "RMI",  # Ріміні, Італія
    "ATH",  # Афіни, Греція
    "SKG",  # Салоніки, Греція
    "HER",  # Іракліон (Крит), Греція
    "CHQ",  # Ханья (Крит), Греція
    "RHO",  # Родос, Греція
    "KGS",  # Кос, Греція
    "CFU",  # Корфу, Греція
    "ZTH",  # Закінф, Греція
    "JMK",  # Міконос, Греція
    "JTR",  # Санторіні, Греція
    "MLA",  # Мальта
    "TLV",  # Тель-Авів, Ізраїль (поруч з Євр.)
    "IST",  # Стамбул, Туреччина
    "SAW",  # Стамбул Сабіха, Туреччина
    "AYT",  # Анталія, Туреччина
    "ADB",  # Ізмір, Туреччина
    "ESB",  # Анкара, Туреччина
    "DLM",  # Даламан, Туреччина
    "BJV",  # Бодрум, Туреччина
    "GZT",  # Газіантеп, Туреччина

    # ── КІПР ──
    "LCA",  # Ларнака, Кіпр
    "PFO",  # Пафос, Кіпр
]

# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
chat_id_storage = {}

AVERAGE_PRICES = {
    "oneway": 110,
    "return": 190,
}


async def fetch_deals(one_way: bool) -> list:
    """Пошук квитків — one-way або return"""
    all_deals = []
    date_from = datetime.now() + timedelta(days=7)

    # Розбиваємо на батчі по 10 аеропортів щоб не перевантажити API
    batch_size = 10
    batches = [ORIGIN_CITIES[i:i+batch_size] for i in range(0, len(ORIGIN_CITIES), batch_size)]

    for batch in batches:
        for origin in batch:
            url = "https://api.travelpayouts.com/aviasales/v3/search_by_price_range"
            params = {
                "origin": origin,
                "destination": "-",
                "value_min": 1,
                "value_max": MAX_PRICE_EUR * 100,
                "one_way": "true" if one_way else "false",
                "direct": "false",
                "locale": "uk",
                "currency": "eur",
                "market": "ua",
                "limit": 10,
                "page": 1,
                "token": TRAVELPAYOUTS_TOKEN,
                "depart_date": date_from.strftime("%Y-%m"),
            }

            if not one_way:
                params["nights_in_dst_from"] = 1
                params["nights_in_dst_to"] = 7

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and data.get("data"):
                                for t in data["data"]:
                                    price = t.get("price", 0) / 100

                                    nights = None
                                    if not one_way:
                                        try:
                                            dep = datetime.fromisoformat(t["departure_at"].replace("Z", "+00:00"))
                                            ret = datetime.fromisoformat(t["return_at"].replace("Z", "+00:00"))
                                            nights = (ret - dep).days
                                            if nights > 7:
                                                continue
                                        except:
                                            pass

                                    all_deals.append({
                                        "type": "oneway" if one_way else "return",
                                        "origin": t.get("origin", origin),
                                        "destination": t.get("destination", ""),
                                        "price": price,
                                        "airline": t.get("airline", ""),
                                        "departure_at": t.get("departure_at", ""),
                                        "return_at": t.get("return_at", "") if not one_way else None,
                                        "transfers": t.get("transfers", 0),
                                        "nights": nights,
                                        "link": f"https://www.aviasales.com{t.get('link', '')}",
                                    })
            except Exception as e:
                logger.error(f"Помилка {origin}: {e}")

            await asyncio.sleep(0.3)

    all_deals.sort(key=lambda x: x["price"])
    return all_deals


def calc_discount(price: float, trip_type: str) -> tuple:
    avg = AVERAGE_PRICES.get(trip_type, 150)
    discount = round((avg - price) / avg * 100) if price < avg else 0
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


def format_section(deals: list, trip_type: str) -> str:
    if trip_type == "oneway":
        msg = "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🛫 *ВАРІАНТ 1 — В ОДИН БІК*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        msg = "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🔄 *ВАРІАНТ 2 — ТУДИ І НАЗАД (до 7 ночей)*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if not deals:
        return msg + "😔 Deals не знайдено\n\n"

    seen = set()
    count = 0

    for deal in deals:
        key = f"{deal['origin']}-{deal['destination']}"
        if key in seen:
            continue
        seen.add(key)
        if count >= TOP_DEALS_COUNT:
            break

        avg, discount = calc_discount(deal["price"], trip_type)
        dep_date = format_date(deal["departure_at"])
        stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"

        fire = "🔥🔥🔥" if discount >= 40 else "🔥🔥" if discount >= 20 else "🔥" if discount > 0 else "💰"

        msg += f"{fire} *{deal['origin']} → {deal['destination']}*\n"
        msg += f"💶 *€{deal['price']:.0f}*"
        if trip_type == "return":
            msg += " туди-назад"
        msg += "\n"

        if discount > 0:
            msg += f"📊 Середня ~€{avg} | Дешевше на *{discount}%*\n"
        else:
            msg += f"📊 Середня ~€{avg}\n"

        msg += f"📅 {dep_date}"
        if trip_type == "return":
            ret_date = format_date(deal.get("return_at", ""))
            nights_str = f" ({deal['nights']} н.)" if deal.get("nights") else ""
            msg += f" — {ret_date}{nights_str}"
        msg += f" | {stops} | {deal['airline']}\n"
        msg += f"🔗 [Дивитись на Aviasales]({deal['link']})\n\n"
        count += 1

    return msg


def format_full_message(oneway: list, returns: list) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"✈️ *FLIGHT DEALS* — {now}\n"
    msg += f"🌍 Пошук по {len(ORIGIN_CITIES)} аеропортах Європи\n\n"
    msg += format_section(oneway, "oneway")
    msg += format_section(returns, "return")
    msg += "💡 _Ціни змінюються — бронюй швидко!_"
    return msg


async def search_and_send(chat_id: int):
    oneway = await fetch_deals(one_way=True)
    returns = await fetch_deals(one_way=False)
    message = format_full_message(oneway, returns)
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
            logger.error(f"Помилка: {e}")


@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id_storage["user"] = message.chat.id
    await message.answer(
        "👋 *Привіт! Я Flight Deals Bot*\n\n"
        f"Шукаю дешеві квитки по *{len(ORIGIN_CITIES)} аеропортах Європи* — "
        "куди завгодно по світу! ✈️\n\n"
        "🛫 *Варіант 1* — в один бік\n"
        "🔄 *Варіант 2* — туди-назад до 7 ночей\n"
        "📊 З розрахунком % знижки від середньої ціни\n\n"
        "⚡ Запускаю пошук... (може зайняти ~30 сек)",
        parse_mode="Markdown"
    )
    searching = await message.answer("🔍 Перевіряю всі аеропорти...")
    await search_and_send(message.chat.id)
    await searching.delete()


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    chat_id_storage["user"] = message.chat.id
    searching = await message.answer("🔍 Шукаю deals по всій Європі... ~30 сек")
    await search_and_send(message.chat.id)
    await searching.delete()


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight Deals Bot*\n\n"
        "/start — підписатись\n"
        "/deals — deals прямо зараз\n"
        "/help — довідка\n\n"
        f"🌍 Покриття: {len(ORIGIN_CITIES)} аеропортів Європи\n"
        "🕘 Автоматично щодня о 9:00\n\n"
        "Найближчі до України: Жешув, Люблін, Краків, Будапешт, Кошіце, Клуж...",
        parse_mode="Markdown"
    )


async def main():
    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    scheduler.start()
    logger.info(f"Бот запущено! {len(ORIGIN_CITIES)} аеропортів ✈️")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
