import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (Message, CallbackQuery,
                           InlineKeyboardMarkup, InlineKeyboardButton, BotCommand)
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# НАЛАШТУВАННЯ
# ============================================================
TELEGRAM_TOKEN = "8602308787:AAFhZMfMNCcTv-yXTDB1mouUFaOBrO_Jac8"
TRAVELPAYOUTS_TOKEN = "83ab9d18d7fb0092294828b8104b50a5"

TOTAL_BUDGET = 400      # загальний бюджет €
TOP_DEALS_COUNT = 5

# ============================================================
# НАЗВИ АЕРОПОРТІВ
# ============================================================
AIRPORT_NAMES = {
    # Польща
    "WAW": "Варшава", "KRK": "Краків", "RZE": "Жешув", "WRO": "Вроцлав",
    "GDN": "Гданськ", "KTW": "Катовіце", "POZ": "Познань", "SZZ": "Щецін",
    "LUZ": "Люблін", "BZG": "Бидгощ", "IEG": "Зелена Гура",
    # Угорщина
    "BUD": "Будапешт", "DEB": "Дебрецен",
    # Чехія / Словаччина
    "PRG": "Прага", "BRQ": "Брно", "BTS": "Братислава", "KSC": "Кошіце", "PZY": "Пьєштяни",
    # Румунія (ВСІ аеропорти)
    "OTP": "Бухарест (Отопень)", "BBU": "Бухарест (Бенесе)",
    "CLJ": "Клуж-Напока", "TSR": "Тімішоара", "IAS": "Яси",
    "SCV": "Сучава", "BCM": "Бакеу", "SBZ": "Сібіу",
    "OMR": "Орадя", "SUJ": "Сату-Маре", "TGM": "Тирґу-Муреш",
    "CRA": "Крайова", "TCE": "Тулча", "BAY": "Бая-Маре",
    "GSR": "Ґура-Гуморулуй",
    # Молдова
    "RMO": "Кишинів",
    # Балкани
    "BEG": "Белград", "INI": "Ніш", "ZAG": "Загреб", "OSI": "Осієк",
    "SPU": "Спліт", "DBV": "Дубровник", "ZAD": "Задар", "PUY": "Пула",
    "RJK": "Рієка",
    "SKP": "Скоп'є", "OHD": "Охрид",
    "TIA": "Тирана",
    "TGD": "Подгориця", "TIV": "Тіват",
    "SOF": "Софія", "PDV": "Пловдів", "VAR": "Варна", "BOJ": "Бургас",
    # Австрія / Швейцарія
    "VIE": "Відень", "GRZ": "Грац", "INN": "Інсбрук", "SZG": "Зальцбург", "LNZ": "Лінц",
    "ZRH": "Цюрих", "GVA": "Женева", "BSL": "Базель",
    # Німеччина
    "MUC": "Мюнхен", "FRA": "Франкфурт", "BER": "Берлін", "HAM": "Гамбург",
    "DUS": "Дюссельдорф", "STR": "Штутгарт", "CGN": "Кельн", "NUE": "Нюрнберг",
    "LEJ": "Лейпциг", "DRS": "Дрезден", "BRE": "Бремен", "FMM": "Меммінген",
    "HHN": "Франкфурт-Хан", "DTM": "Дортмунд", "PAD": "Падерборн",
    "ERF": "Ерфурт", "SCN": "Саарбрюккен", "NRN": "Вайзе",
    # Франція
    "CDG": "Париж (CDG)", "ORY": "Париж (Орлі)", "LYS": "Ліон", "MRS": "Марсель",
    "NCE": "Ніцца", "TLS": "Тулуза", "BOD": "Бордо", "NTE": "Нант",
    "SXB": "Страсбург", "MPL": "Монпельє", "BES": "Брест", "LIL": "Лілль",
    "BIA": "Бастія", "AJA": "Аяччо",
    # Велика Британія / Ірландія
    "LHR": "Лондон (Хітроу)", "LGW": "Лондон (Гетвік)", "STN": "Лондон (Станстед)",
    "LTN": "Лондон (Лутон)", "LCY": "Лондон (Сіті)", "MAN": "Манчестер",
    "BHX": "Бірмінгем", "EDI": "Единбург", "GLA": "Глазго", "BRS": "Брістоль",
    "NCL": "Ньюкасл", "LPL": "Ліверпуль", "EMA": "Іст-Мідлендс", "ABZ": "Абердін",
    "BFS": "Белфаст", "DUB": "Дублін", "SNN": "Шеннон", "ORK": "Корк", "NOC": "Ноккі",
    # Нідерланди / Бельгія / Люксембург
    "AMS": "Амстердам", "EIN": "Ейндговен", "RTM": "Роттердам", "GRQ": "Гронінген",
    "BRU": "Брюссель", "CRL": "Брюссель (Шарлеруа)", "LGG": "Льєж", "LUX": "Люксембург",
    # Іспанія
    "MAD": "Мадрид", "BCN": "Барселона", "AGP": "Малага", "ALC": "Аліканте",
    "PMI": "Пальма (Майорка)", "IBZ": "Ібіца", "VLC": "Валенсія", "SVQ": "Севілья",
    "BIO": "Більбао", "SDR": "Сантандер", "SCQ": "Сантьяго", "OVD": "Ов'єдо",
    "VGO": "Віго", "GRX": "Гранада", "MHN": "Менорка",
    "ACE": "Ланзароте", "TFS": "Тенеріфе (пд)", "TFN": "Тенеріфе (пн)",
    "LPA": "Гран Канарія", "FUE": "Фуертевентура",
    # Португалія
    "LIS": "Лісабон", "OPO": "Порту", "FAO": "Фару", "FNC": "Мадейра", "PDL": "Азори",
    # Скандинавія
    "CPH": "Копенгаген", "AAL": "Ольборг", "BLL": "Більунд",
    "ARN": "Стокгольм", "NYO": "Стокгольм (Скавста)", "GOT": "Гетеборг", "MMX": "Мальме",
    "OSL": "Осло", "TRF": "Осло (Торп)", "BGO": "Берген", "SVG": "Ставангер", "TRD": "Тронгейм",
    "HEL": "Гельсінкі", "TMP": "Тампере", "TKU": "Турку", "OUL": "Оулу",
    "KEF": "Рейк'явік",
    # Балтія
    "RIX": "Рига", "TLL": "Таллін", "VNO": "Вільнюс", "KUN": "Каунас", "PLQ": "Паланга",
    # Італія
    "FCO": "Рим (Фьюмічино)", "CIA": "Рим (Чампіно)",
    "MXP": "Мілан (Мальпенса)", "LIN": "Мілан (Лінате)", "BGY": "Мілан (Бергамо)",
    "VCE": "Венеція", "TSF": "Тревізо", "NAP": "Неаполь", "BRI": "Барі",
    "BLQ": "Болонья", "FLR": "Флоренція", "PSA": "Піза", "VRN": "Верона",
    "TRS": "Трієст", "CAG": "Кальярі", "OLB": "Ольбія", "AHO": "Алгеро",
    "CTA": "Катанія", "PMO": "Палермо", "PSR": "Пескара", "RMI": "Ріміні",
    # Греція / Кіпр / Мальта
    "ATH": "Афіни", "SKG": "Салоніки", "HER": "Іракліон (Крит)",
    "CHQ": "Ханья (Крит)", "RHO": "Родос", "KGS": "Кос", "CFU": "Корфу",
    "ZTH": "Закінф", "JMK": "Міконос", "JTR": "Санторіні", "KLX": "Каламата",
    "LCA": "Ларнака (Кіпр)", "PFO": "Пафос (Кіпр)", "MLA": "Мальта",
    # Туреччина
    "IST": "Стамбул", "SAW": "Стамбул (Сабіха)", "AYT": "Анталія",
    "ADB": "Ізмір", "ESB": "Анкара", "DLM": "Даламан", "BJV": "Бодрум", "GZT": "Газіантеп",
    # Інше
    "TLV": "Тель-Авів",
}

# Регіони
REGIONS = {
    "🌍 Всюди": [],
    "🏖 Середземномор'я": ["FCO","CIA","MXP","BGY","VCE","NAP","BLQ","FLR","PSA","CTA","PMO",
                           "ATH","SKG","HER","RHO","KGS","CFU","ZTH","JMK","JTR",
                           "LCA","PFO","MLA","PMI","IBZ","AGP","BCN","MAD","AYT","DLM","BJV"],
    "🇷🇴 Румунія/Молдова": ["OTP","CLJ","TSR","IAS","SCV","BCM","SBZ","OMR","SUJ","TGM","CRA","RMO"],
    "🏔 Балкани":          ["BEG","INI","ZAG","SPU","DBV","SKP","TIA","TGD","TIV","SOF","VAR","BOJ"],
    "❄️ Скандинавія":     ["CPH","ARN","GOT","OSL","BGO","HEL","TMP","KEF"],
    "🏰 Центр Європи":    ["VIE","PRG","BUD","ZRH","GVA","MUC","FRA","BER"],
    "🇬🇧 Британія/Ірл":  ["LHR","LGW","STN","MAN","EDI","DUB"],
    "🌊 Канари":           ["ACE","TFS","TFN","LPA","FUE"],
    "🇵🇱 Польща/Балтія": ["WAW","KRK","RZE","WRO","GDN","KTW","BUD","RIX","TLL","VNO"],
}

# Аеропорти для пошуку вильоту
ORIGIN_CITIES = [
    "WAW","KRK","RZE","WRO","GDN","KTW","POZ","LUZ",
    "BUD","DEB","PRG","BRQ","BTS","KSC",
    "OTP","CLJ","TSR","IAS","SCV","BCM","SBZ","OMR","SUJ","TGM","CRA",
    "RMO",
    "VIE","GRZ","SZG","ZRH","GVA","BSL",
    "MUC","FRA","BER","HAM","DUS","STR","CGN","NUE","LEJ","DRS","BRE","FMM","HHN","DTM",
    "CDG","ORY","LYS","MRS","NCE","TLS","BOD","NTE","SXB","LIL",
    "LHR","LGW","STN","LTN","MAN","BHX","EDI","GLA","BRS","NCL","LPL",
    "AMS","EIN","BRU","CRL","LGG","LUX",
    "FCO","MXP","VCE","NAP","BLQ","PSA","VRN","BRI","CTA","PMO",
    "MAD","BCN","AGP","VLC","PMI","SVQ","BIO",
    "LIS","OPO","FAO",
    "ATH","SKG","HER","RHO","CFU",
    "CPH","ARN","GOT","OSL","HEL","TMP",
    "RIX","TLL","VNO","KUN",
    "DUB",
    "SOF","VAR","BEG","ZAG","SPU","DBV",
    "IST","SAW","AYT",
    "LCA","PFO","MLA",
    "TLV",
]

AVERAGE_PRICES = {"oneway": 110, "return": 185}

# FlixBus міста (id для посилань)
FLIXBUS_CITIES = {
    "Варшава": "88", "Краків": "28", "Жешув": "1292", "Вроцлав": "91",
    "Будапешт": "26", "Прага": "76", "Братислава": "78", "Відень": "1",
    "Берлін": "2", "Мюнхен": "3", "Франкфурт": "5", "Гамбург": "23",
    "Париж": "13", "Ліон": "30", "Барселона": "22", "Мадрид": "17",
    "Рим": "82", "Мілан": "7", "Венеція": "81", "Амстердам": "57",
    "Брюссель": "25", "Бухарест": "395", "Клуж": "393", "Яси": "396",
    "Кишинів": "400", "Белград": "389", "Загреб": "162", "Софія": "386",
    "Лісабон": "45", "Порту": "47",
}

# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

user_settings = {}
watchlist = {}
last_deals_cache = {}  # кеш попередніх deals для порівняння


def get_settings(chat_id: int) -> dict:
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "budget": TOTAL_BUDGET,
            "region": "🌍 Всюди",
            "origins": list(ORIGIN_CITIES),
            "one_way": True,
            "return_trip": True,
            "with_hotel": True,
            "max_nights": 5,
        }
    return user_settings[chat_id]


def ap(code: str) -> str:
    name = AIRPORT_NAMES.get(code, "")
    return f"{code} ({name})" if name and name != code else code


# ============================================================
# АВІА API
# ============================================================

async def fetch_flights(session, origin: str, one_way: bool,
                        flight_budget: int, region_filter: list) -> list:
    results = []
    now = datetime.now()
    for i in range(1, 4):
        month = (now + timedelta(days=30 * i)).strftime("%Y-%m")
        params = {
            "origin": origin,
            "depart_date": month,
            "currency": "eur",
            "token": TRAVELPAYOUTS_TOKEN,
            "one_way": "true" if one_way else "false",
        }
        if not one_way:
            params["return_date"] = (now + timedelta(days=30 * i + 5)).strftime("%Y-%m")

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
                            if region_filter and dest not in region_filter:
                                continue
                            for _, t in tickets.items():
                                price = t.get("price", 0)
                                if price <= 0 or price > flight_budget:
                                    continue
                                nights = None
                                if not one_way:
                                    try:
                                        dep = datetime.fromisoformat(t["departure_at"].replace("Z", "+00:00"))
                                        ret = datetime.fromisoformat(t["return_at"].replace("Z", "+00:00"))
                                        nights = (ret - dep).days
                                        if nights < 1 or nights > 7:
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
            logger.warning(f"Авіа {origin}: {e}")
    return results


async def fetch_all_flights(one_way: bool, settings: dict) -> list:
    budget = settings["budget"]
    region = settings["region"]
    origins = settings["origins"]
    region_filter = REGIONS.get(region, [])

    # Якщо є готель — ліміт на квиток = 70% бюджету
    if settings["with_hotel"] and not one_way:
        flight_budget = int(budget * 0.70)
    else:
        flight_budget = budget

    all_deals = []
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        batch_size = 8
        for i in range(0, len(origins), batch_size):
            batch = origins[i:i + batch_size]
            tasks = [fetch_flights(session, o, one_way, flight_budget, region_filter) for o in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_deals.extend(r)
            await asyncio.sleep(0.5)

    seen = set()
    unique = []
    for d in sorted(all_deals, key=lambda x: x["price"]):
        key = f"{d['origin']}-{d['destination']}"
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


# ============================================================
# ГОТЕЛЬНИЙ API (Hotellook cache)
# ============================================================

async def fetch_hotel(destination: str, check_in: str, check_out: str,
                      max_hotel_budget: int) -> dict | None:
    """Шукаємо найдешевший готель/хостел через Hotellook cache API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://engine.hotellook.com/api/v2/cache.json",
                params={
                    "location": destination,
                    "checkIn": check_in,
                    "checkOut": check_out,
                    "currency": "eur",
                    "limit": 5,
                    "token": TRAVELPAYOUTS_TOKEN,
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and data:
                        # Беремо найдешевший
                        cheapest = min(data, key=lambda h: h.get("priceFrom", 9999))
                        price = cheapest.get("priceFrom", 0)
                        if price > 0 and price <= max_hotel_budget:
                            hotel_id = cheapest.get("hotelId", "")
                            return {
                                "name": cheapest.get("hotelName", "Готель"),
                                "stars": cheapest.get("stars", 0),
                                "price": price,
                                "rating": cheapest.get("pricePercentile", {}).get("50", 0),
                                "link": f"https://hotels.aviasales.ru/r/pricelist/v2?location={destination}&checkIn={check_in}&checkOut={check_out}&currency=eur&token={TRAVELPAYOUTS_TOKEN}",
                            }
    except Exception as e:
        logger.warning(f"Готель {destination}: {e}")
    return None


# ============================================================
# ФОРМАТУВАННЯ
# ============================================================

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


def get_check_dates(departure_at: str, nights: int) -> tuple:
    """Повертає дати check-in та check-out"""
    try:
        dep = datetime.fromisoformat(departure_at.replace("Z", "+00:00"))
        check_in = dep.strftime("%Y-%m-%d")
        check_out = (dep + timedelta(days=nights)).strftime("%Y-%m-%d")
        return check_in, check_out
    except:
        now = datetime.now()
        return now.strftime("%Y-%m-%d"), (now + timedelta(days=3)).strftime("%Y-%m-%d")


async def format_deal(deal: dict, one_way: bool, settings: dict, idx: int) -> str:
    trip_type = "oneway" if one_way else "return"
    avg, discount = calc_discount(deal["price"], trip_type)
    dep_date = format_date(deal["departure_at"])
    stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
    fire = "🔥🔥🔥" if discount >= 40 else "🔥🔥" if discount >= 20 else "🔥" if discount > 0 else "💰"

    orig = ap(deal["origin"])
    dest = ap(deal["destination"])

    msg = f"{fire} *{orig} → {dest}*\n"
    msg += f"✈️ *€{deal['price']:.0f}*"
    if not one_way:
        msg += " туди-назад"
    msg += "\n"
    if discount > 0:
        msg += f"📊 ~€{avg} середня | дешевше на *{discount}%*\n"
    msg += f"📅 {dep_date}"

    hotel_block = ""
    total_price = deal["price"]

    if not one_way and settings["with_hotel"] and deal.get("nights"):
        nights = deal["nights"]
        ret_date = format_date(deal.get("return_at", ""))
        msg += f" — {ret_date} · {nights} н."
        check_in, check_out = get_check_dates(deal["departure_at"], nights)

        max_hotel = settings["budget"] - deal["price"]
        if max_hotel > 10:
            hotel = await fetch_hotel(deal["destination"], check_in, check_out, max_hotel)
            if hotel:
                total_price = deal["price"] + hotel["price"]
                stars_str = "⭐" * int(hotel["stars"]) if hotel["stars"] else "🏨"
                hotel_block = (
                    f"\n{stars_str} *{hotel['name']}*\n"
                    f"🛏 €{hotel['price']:.0f} за {nights} н.\n"
                    f"🔗 [Дивитись готель]({hotel['link']})\n"
                    f"💰 *РАЗОМ: €{total_price:.0f}* / бюджет €{settings['budget']}"
                )
                if total_price <= settings["budget"]:
                    hotel_block += " ✅"

    msg += f" | {stops} | {deal['airline']}\n"
    msg += f"🔗 [Aviasales]({deal['link']})"
    if hotel_block:
        msg += hotel_block
    msg += "\n\n"
    return msg


async def format_section(deals: list, one_way: bool, settings: dict) -> str:
    if one_way:
        msg = "━━━━━━━━━━━━━━━━━━━━\n🛫 *В ОДИН БІК*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        hotel_note = " + 🏨 готель" if settings["with_hotel"] else ""
        msg = f"━━━━━━━━━━━━━━━━━━━━\n🔄 *ТУДИ І НАЗАД{hotel_note}*\n━━━━━━━━━━━━━━━━━━━━\n\n"

    if not deals:
        return msg + "😔 Немає даних — спробуй пізніше\n\n"

    count = 0
    for i, deal in enumerate(deals):
        if count >= TOP_DEALS_COUNT:
            break
        msg += await format_deal(deal, one_way, settings, i)
        count += 1
    return msg


async def do_search(chat_id: int) -> str:
    s = get_settings(chat_id)
    tasks = []
    flags = []
    if s["one_way"]:
        tasks.append(fetch_all_flights(True, s))
        flags.append(True)
    if s["return_trip"]:
        tasks.append(fetch_all_flights(False, s))
        flags.append(False)

    results = await asyncio.gather(*tasks)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    hotel_note = " + 🏨" if s["with_hotel"] else ""
    msg = f"✈️ *FLIGHT DEALS{hotel_note}* — {now}\n"
    msg += f"💶 Бюджет €{s['budget']} | 🌍 {s['region']}\n\n"

    for i, (flag, deals) in enumerate(zip(flags, results)):
        msg += await format_section(deals, flag, s)

    msg += "💡 _Ціни з кешу Aviasales_"
    return msg, results, flags


# ============================================================
# FLIXBUS
# ============================================================

def flixbus_next_month_links() -> str:
    now = datetime.now()
    next_month = (now + timedelta(days=30)).strftime("%d.%m.%Y")
    month_name_ua = ["","Січень","Лютий","Березень","Квітень","Травень","Червень",
                     "Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"]
    next_m = (now.month % 12) + 1
    month_name = month_name_ua[next_m]

    msg = f"🚌 *FlixBus — {month_name} {now.year + (1 if next_m == 1 else 0)}*\n\n"
    msg += "Дешеві автобусні маршрути на наступний місяць:\n\n"

    routes = [
        ("Краків", "Варшава", "28", "88"),
        ("Краків", "Відень", "28", "1"),
        ("Краків", "Берлін", "28", "2"),
        ("Варшава", "Берлін", "88", "2"),
        ("Варшава", "Прага", "88", "76"),
        ("Варшава", "Будапешт", "88", "26"),
        ("Будапешт", "Відень", "26", "1"),
        ("Будапешт", "Братислава", "26", "78"),
        ("Відень", "Прага", "1", "76"),
        ("Відень", "Братислава", "1", "78"),
        ("Бухарест", "Клуж", "395", "393"),
        ("Кишинів", "Бухарест", "400", "395"),
        ("Яси", "Бухарест", "396", "395"),
    ]

    for from_city, to_city, from_id, to_id in routes:
        url = (f"https://shop.global.flixbus.com/s?"
               f"departureCity={from_id}&arrivalCity={to_id}"
               f"&rideDate={next_month}&adult=1&currency=EUR")
        msg += f"🚌 [{from_city} → {to_city}]({url})\n"

    msg += f"\n🔍 [Всі маршрути FlixBus](https://www.flixbus.com)\n"
    msg += f"\n💡 _Натисни на маршрут щоб перевірити ціни на {month_name}_"
    return msg


# ============================================================
# КЛАВІАТУРИ
# ============================================================

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Шукати deals", callback_data="search")],
        [InlineKeyboardButton(text="🚌 FlixBus наступний місяць", callback_data="flixbus")],
        [InlineKeyboardButton(text="💶 Бюджет", callback_data="menu_budget"),
         InlineKeyboardButton(text="🌍 Регіон", callback_data="menu_region")],
        [InlineKeyboardButton(text="🏨 Готель: вкл/викл", callback_data="toggle_hotel"),
         InlineKeyboardButton(text="🛫 Тип рейсу", callback_data="menu_type")],
        [InlineKeyboardButton(text="⭐ Watchlist", callback_data="menu_watchlist")],
    ])


def budget_kb() -> InlineKeyboardMarkup:
    budgets = [100, 150, 200, 250, 300, 400, 500]
    rows = [[InlineKeyboardButton(text=f"€{b}", callback_data=f"budget_{b}") for b in budgets[:4]],
            [InlineKeyboardButton(text=f"€{b}", callback_data=f"budget_{b}") for b in budgets[4:]],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def region_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=r, callback_data=f"region_{r}")] for r in REGIONS]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def type_kb(chat_id: int) -> InlineKeyboardMarkup:
    s = get_settings(chat_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if s['one_way'] else '☐'} В один бік", callback_data="toggle_oneway")],
        [InlineKeyboardButton(text=f"{'✅' if s['return_trip'] else '☐'} Туди-назад", callback_data="toggle_return")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def watchlist_kb(chat_id: int) -> InlineKeyboardMarkup:
    watches = watchlist.get(chat_id, [])
    rows = []
    for i, w in enumerate(watches):
        rows.append([InlineKeyboardButton(
            text=f"🗑 {w['origin']}→{w['destination']} (до €{w['threshold']})",
            callback_data=f"unwatch_{i}"
        )])
    rows.append([InlineKeyboardButton(text="➕ /watch KRK FCO 80", callback_data="noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ============================================================
# ХЕНДЛЕРИ
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    get_settings(chat_id)
    await message.answer(
        "👋 *Привіт! Я Flight + Hotel Deals Bot* ✈️🏨\n\n"
        f"Шукаю найдешевші *квитки + готель* по {len(ORIGIN_CITIES)} аеропортах Європи!\n\n"
        "✈️ В один бік / туди-назад\n"
        "🏨 Автоматично шукаю готель в пакеті\n"
        f"💶 Загальний бюджет: €{TOTAL_BUDGET} (квиток + готель)\n"
        "🚌 FlixBus — дешеві автобуси на наступний місяць\n"
        "⭐ Watchlist — сповіщення про зниження цін\n\n"
        "👇 Використовуй меню:",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    wait = await message.answer("🔍 Шукаю deals + готелі (~40 сек)...")
    result = await do_search(message.chat.id)
    msg = result[0]
    await wait.delete()
    await message.answer(msg, parse_mode="Markdown",
                         disable_web_page_preview=True,
                         reply_markup=main_menu_kb())


@dp.message(Command("flixbus"))
async def cmd_flixbus(message: Message):
    msg = flixbus_next_month_links()
    await message.answer(msg, parse_mode="Markdown",
                         disable_web_page_preview=True,
                         reply_markup=main_menu_kb())


@dp.message(Command("watch"))
async def cmd_watch(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "⭐ *Watchlist*\n\nФормат: `/watch ЗВІДКИ КУДИ ЦІНА`\n"
            "Приклад: `/watch KRK LCA 60`\n\n"
            "Бот сповістить коли ціна впаде нижче вказаної!",
            parse_mode="Markdown"
        )
        return
    origin = parts[1].upper()
    destination = parts[2].upper()
    threshold = int(parts[3]) if len(parts) > 3 else 80
    chat_id = message.chat.id
    if chat_id not in watchlist:
        watchlist[chat_id] = []
    for w in watchlist[chat_id]:
        if w["origin"] == origin and w["destination"] == destination:
            await message.answer("ℹ️ Цей маршрут вже у watchlist!")
            return
    watchlist[chat_id].append({"origin": origin, "destination": destination, "threshold": threshold})
    await message.answer(
        f"⭐ Додано!\n*{ap(origin)} → {ap(destination)}*\nСповіщу коли ціна < €{threshold}",
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight + Hotel Bot*\n\n"
        "/start — головне меню\n"
        "/deals — пошук зараз\n"
        "/flixbus — автобуси наступний місяць\n"
        "/watch KRK FCO 60 — watchlist\n"
        "/help — довідка\n\n"
        f"🌍 {len(ORIGIN_CITIES)} аеропортів | 🇷🇴 Вся Румунія | 🇲🇩 Молдова\n"
        "🕘 Авто-пошук о 9:00 | Watchlist кожні 3 год",
        parse_mode="Markdown"
    )


# ── Callback кнопки ──

@dp.callback_query(F.data == "search")
async def cb_search(cb: CallbackQuery):
    await cb.answer()
    wait = await cb.message.answer("🔍 Шукаю deals + готелі (~40 сек)...")
    result = await do_search(cb.message.chat.id)
    msg = result[0]
    await wait.delete()
    await cb.message.answer(msg, parse_mode="Markdown",
                             disable_web_page_preview=True,
                             reply_markup=main_menu_kb())


@dp.callback_query(F.data == "flixbus")
async def cb_flixbus(cb: CallbackQuery):
    await cb.answer()
    msg = flixbus_next_month_links()
    await cb.message.answer(msg, parse_mode="Markdown",
                             disable_web_page_preview=True,
                             reply_markup=main_menu_kb())


@dp.callback_query(F.data == "back_main")
async def cb_back(cb: CallbackQuery):
    await cb.answer()
    s = get_settings(cb.message.chat.id)
    hotel_str = "✅" if s["with_hotel"] else "❌"
    await cb.message.edit_text(
        f"⚙️ *Налаштування:*\n\n"
        f"💶 Бюджет: €{s['budget']} | 🌍 {s['region']}\n"
        f"🏨 Готель в пакеті: {hotel_str}\n"
        f"🛫 {'✅' if s['one_way'] else '❌'} В один бік | "
        f"🔄 {'✅' if s['return_trip'] else '❌'} Туди-назад",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data == "menu_budget")
async def cb_menu_budget(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("💶 *Загальний бюджет (квиток + готель):*",
                                parse_mode="Markdown", reply_markup=budget_kb())


@dp.callback_query(F.data.startswith("budget_"))
async def cb_budget(cb: CallbackQuery):
    b = int(cb.data.split("_")[1])
    get_settings(cb.message.chat.id)["budget"] = b
    await cb.answer(f"✅ Бюджет: €{b}")
    await cb.message.edit_text(f"✅ Бюджет встановлено: *€{b}*",
                                parse_mode="Markdown", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "menu_region")
async def cb_menu_region(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🌍 *Регіон призначення:*",
                                parse_mode="Markdown", reply_markup=region_kb())


@dp.callback_query(F.data.startswith("region_"))
async def cb_region(cb: CallbackQuery):
    region = cb.data[7:]
    get_settings(cb.message.chat.id)["region"] = region
    await cb.answer(f"✅ {region}")
    await cb.message.edit_text(f"✅ Регіон: *{region}*",
                                parse_mode="Markdown", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "toggle_hotel")
async def cb_toggle_hotel(cb: CallbackQuery):
    s = get_settings(cb.message.chat.id)
    s["with_hotel"] = not s["with_hotel"]
    status = "✅ увімкнено" if s["with_hotel"] else "❌ вимкнено"
    await cb.answer(f"🏨 Готель {status}")
    await cb.message.edit_reply_markup(reply_markup=main_menu_kb())


@dp.callback_query(F.data == "menu_type")
async def cb_menu_type(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🛫 *Тип рейсу:*",
                                parse_mode="Markdown", reply_markup=type_kb(cb.message.chat.id))


@dp.callback_query(F.data == "toggle_oneway")
async def cb_toggle_oneway(cb: CallbackQuery):
    s = get_settings(cb.message.chat.id)
    s["one_way"] = not s["one_way"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=type_kb(cb.message.chat.id))


@dp.callback_query(F.data == "toggle_return")
async def cb_toggle_return(cb: CallbackQuery):
    s = get_settings(cb.message.chat.id)
    s["return_trip"] = not s["return_trip"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=type_kb(cb.message.chat.id))


@dp.callback_query(F.data == "menu_watchlist")
async def cb_menu_watchlist(cb: CallbackQuery):
    await cb.answer()
    watches = watchlist.get(cb.message.chat.id, [])
    text = "⭐ *Watchlist*\n\n"
    if watches:
        for w in watches:
            text += f"• {ap(w['origin'])} → {ap(w['destination'])} — до €{w['threshold']}\n"
    else:
        text += "_Порожньо._\nДодай: `/watch KRK LCA 60`"
    await cb.message.edit_text(text, parse_mode="Markdown",
                                reply_markup=watchlist_kb(cb.message.chat.id))


@dp.callback_query(F.data.startswith("unwatch_"))
async def cb_unwatch(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    chat_id = cb.message.chat.id
    if chat_id in watchlist and idx < len(watchlist[chat_id]):
        watchlist[chat_id].pop(idx)
        await cb.answer("🗑 Видалено")
    await cb.message.edit_reply_markup(reply_markup=watchlist_kb(chat_id))


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery): await cb.answer()


# ============================================================
# АВТО-ОНОВЛЕННЯ (якщо з'явились нові deals)
# ============================================================

async def check_new_deals():
    """Перевіряємо чи з'явились нові deals дешевші ніж раніше"""
    for chat_id in list(user_settings.keys()):
        try:
            s = get_settings(chat_id)
            result = await do_search(chat_id)
            deals_list = result[1]
            flags = result[2]

            new_best = {}
            for deals, flag in zip(deals_list, flags):
                key = "oneway" if flag else "return"
                if deals:
                    new_best[key] = deals[0]["price"]

            prev = last_deals_cache.get(chat_id, {})
            alerts = []

            for key, price in new_best.items():
                if key in prev:
                    if price < prev[key] * 0.85:  # ціна впала більше ніж на 15%
                        type_str = "one-way" if key == "oneway" else "туди-назад"
                        alerts.append(f"📉 Нова низька ціна ({type_str}): *€{price:.0f}* (була €{prev[key]:.0f})")

            last_deals_cache[chat_id] = new_best

            if alerts:
                alert_msg = "🔔 *НОВІ DEALS!*\n\n" + "\n".join(alerts)
                alert_msg += "\n\nНатисни /deals щоб переглянути!"
                await bot.send_message(chat_id, alert_msg, parse_mode="Markdown",
                                       reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"check_new_deals: {e}")


async def check_watchlist():
    for chat_id, watches in list(watchlist.items()):
        for w in watches:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        "origin": w["origin"], "destination": w["destination"],
                        "currency": "eur", "token": TRAVELPAYOUTS_TOKEN,
                    }
                    async with session.get(
                        "https://api.travelpayouts.com/v1/prices/cheap",
                        params=params,
                        headers={"x-access-token": TRAVELPAYOUTS_TOKEN},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("success") and data.get("data"):
                                for dest, tickets in data["data"].items():
                                    if dest != w["destination"]:
                                        continue
                                    for _, t in tickets.items():
                                        price = t.get("price", 0)
                                        if 0 < price <= w["threshold"]:
                                            await bot.send_message(
                                                chat_id,
                                                f"🔔 *WATCHLIST!*\n\n"
                                                f"⭐ *{ap(w['origin'])} → {ap(w['destination'])}*\n"
                                                f"💶 *€{price}* — нижче порогу €{w['threshold']}!\n"
                                                f"🔗 [Aviasales](https://www.aviasales.com/search/{w['origin']}{w['destination']})",
                                                parse_mode="Markdown",
                                                disable_web_page_preview=True
                                            )
            except Exception as e:
                logger.error(f"Watchlist: {e}")
            await asyncio.sleep(0.5)


async def send_daily_deals():
    for chat_id in list(user_settings.keys()):
        try:
            result = await do_search(chat_id)
            msg = result[0]
            await bot.send_message(chat_id, msg, parse_mode="Markdown",
                                   disable_web_page_preview=True,
                                   reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"Daily: {e}")


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="deals", description="Шукати deals зараз"),
        BotCommand(command="flixbus", description="FlixBus наступний місяць"),
        BotCommand(command="watch", description="/watch KRK FCO 60 — відстежувати"),
        BotCommand(command="help", description="Довідка"),
    ])

    # Щоденна розсилка о 9:00
    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    # Перевірка watchlist кожні 3 год
    scheduler.add_job(check_watchlist, "cron", hour="*/3", minute=30)
    # Перевірка нових deals кожні 6 год
    scheduler.add_job(check_new_deals, "cron", hour="*/6", minute=0)

    scheduler.start()
    logger.info("Бот v6 запущено! ✈️🏨🚌")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
