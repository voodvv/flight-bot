import asyncio
import logging
import json
from datetime import datetime, timedelta
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# НАЛАШТУВАННЯ
# ============================================================
TELEGRAM_TOKEN = "8602308787:AAFhZMfMNCcTv-yXTDB1mouUFaOBrO_Jac8"
TRAVELPAYOUTS_TOKEN = "83ab9d18d7fb0092294828b8104b50a5"

TOP_DEALS_COUNT = 5

# ============================================================
# НАЗВИ АЕРОПОРТІВ
# ============================================================
AIRPORT_NAMES = {
    # Польща
    "WAW": "Варшава", "KRK": "Краків", "RZE": "Жешув", "WRO": "Вроцлав",
    "GDN": "Гданськ", "KTW": "Катовіце", "POZ": "Познань", "SZZ": "Щецін",
    # Угорщина
    "BUD": "Будапешт", "DEB": "Дебрецен",
    # Чехія / Словаччина
    "PRG": "Прага", "BRQ": "Брно", "BTS": "Братислава", "KSC": "Кошіце",
    # Румунія / Молдова
    "OTP": "Бухарест", "CLJ": "Клуж", "TSR": "Тімішоара", "IAS": "Яси",
    "SBZ": "Сібіу", "SUJ": "Сату-Маре", "BCM": "Бакеу", "MDU": "Кишинів",
    # Балкани
    "BEG": "Белград", "INI": "Ніш", "ZAG": "Загреб", "OSI": "Осієк",
    "SKP": "Скоп'є", "TIA": "Тирана", "TGD": "Подгориця", "TIV": "Тіват",
    "SOF": "Софія", "PDV": "Пловдів", "VAR": "Варна", "BOJ": "Бургас",
    # Австрія / Швейцарія
    "VIE": "Відень", "GRZ": "Грац", "INN": "Інсбрук", "SZG": "Зальцбург",
    "ZRH": "Цюрих", "GVA": "Женева", "BSL": "Базель",
    # Німеччина
    "MUC": "Мюнхен", "FRA": "Франкфурт", "BER": "Берлін", "HAM": "Гамбург",
    "DUS": "Дюссельдорф", "STR": "Штутгарт", "CGN": "Кельн", "NUE": "Нюрнберг",
    "LEJ": "Лейпциг", "DRS": "Дрезден", "BRE": "Бремен", "FMM": "Меммінген",
    "HHN": "Франкфурт-Хан", "DTM": "Дортмунд", "PAD": "Падерборн",
    # Франція
    "CDG": "Париж (CDG)", "ORY": "Париж (Орлі)", "LYS": "Ліон", "MRS": "Марсель",
    "NCE": "Ніцца", "TLS": "Тулуза", "BOD": "Бордо", "NTE": "Нант",
    "SXB": "Страсбург", "MPL": "Монпельє",
    # Велика Британія / Ірландія
    "LHR": "Лондон (Хітроу)", "LGW": "Лондон (Гетвік)", "STN": "Лондон (Станстед)",
    "LTN": "Лондон (Лутон)", "LCY": "Лондон (Сіті)", "MAN": "Манчестер",
    "BHX": "Бірмінгем", "EDI": "Единбург", "GLA": "Глазго", "BRS": "Брістоль",
    "NCL": "Ньюкасл", "LPL": "Ліверпуль", "EMA": "Іст-Мідлендс",
    "DUB": "Дублін", "SNN": "Шеннон", "ORK": "Корк",
    # Нідерланди / Бельгія / Люксембург
    "AMS": "Амстердам", "EIN": "Ейндговен", "RTM": "Роттердам",
    "BRU": "Брюссель", "CRL": "Брюссель (Шарлеруа)", "LGG": "Льєж",
    "LUX": "Люксембург",
    # Іспанія
    "MAD": "Мадрид", "BCN": "Барселона", "AGP": "Малага", "ALC": "Аліканте",
    "PMI": "Пальма (Майорка)", "IBZ": "Ібіца", "VLC": "Валенсія",
    "SVQ": "Севілья", "BIO": "Більбао", "SCQ": "Сантьяго",
    "ACE": "Ланзароте", "TFS": "Тенеріфе (пд)", "TFN": "Тенеріфе (пн)",
    "LPA": "Гран Канарія", "FUE": "Фуертевентура",
    # Португалія
    "LIS": "Лісабон", "OPO": "Порту", "FAO": "Фару", "FNC": "Мадейра",
    # Скандинавія / Балтія
    "CPH": "Копенгаген", "AAL": "Ольборг", "BLL": "Більунд",
    "ARN": "Стокгольм", "GOT": "Гетеборг", "MMX": "Мальме",
    "OSL": "Осло", "BGO": "Берген", "SVG": "Ставангер",
    "HEL": "Гельсінкі", "TMP": "Тампере", "TKU": "Турку",
    "KEF": "Рейк'явік",
    "RIX": "Рига", "TLL": "Таллін", "VNO": "Вільнюс", "KUN": "Каунас",
    # Італія
    "FCO": "Рим (Фьюмічино)", "CIA": "Рим (Чампіно)", "MXP": "Мілан (Мальпенса)",
    "LIN": "Мілан (Лінате)", "BGY": "Мілан (Бергамо)", "VCE": "Венеція",
    "TSF": "Тревізо", "NAP": "Неаполь", "BRI": "Барі", "BLQ": "Болонья",
    "FLR": "Флоренція", "PSA": "Піза", "VRN": "Верона", "TRS": "Трієст",
    "CAG": "Кальярі", "CTA": "Катанія", "PMO": "Палермо",
    # Греція / Кіпр / Мальта
    "ATH": "Афіни", "SKG": "Салоніки", "HER": "Іракліон (Крит)",
    "CHQ": "Ханья (Крит)", "RHO": "Родос", "KGS": "Кос", "CFU": "Корфу",
    "ZTH": "Закінф", "JMK": "Міконос", "JTR": "Санторіні",
    "LCA": "Ларнака (Кіпр)", "PFO": "Пафос (Кіпр)", "MLA": "Мальта",
    # Туреччина
    "IST": "Стамбул", "SAW": "Стамбул (Сабіха)", "AYT": "Анталія",
    "ADB": "Ізмір", "ESB": "Анкара", "DLM": "Даламан", "BJV": "Бодрум",
    # Інше
    "TLV": "Тель-Авів", "STO": "Стокгольм (Скавста)",
    "SCV": "Сучава (Румунія)", "MIL": "Мілан",
    "IAS": "Яси (Румунія)",
    "RMO": "Кишинів (Молдова)",
}

# Регіони призначення
REGIONS = {
    "🏖 Середземномор'я": ["FCO", "CIA", "MXP", "BGY", "VCE", "NAP", "BLQ", "FLR", "PSA",
                           "ATH", "SKG", "HER", "RHO", "KGS", "CFU", "ZTH", "JMK", "JTR",
                           "LCA", "PFO", "MLA", "PMI", "IBZ", "AGP", "BCN", "MAD",
                           "AYT", "DLM", "BJV"],
    "❄️ Скандинавія":    ["CPH", "ARN", "GOT", "OSL", "BGO", "HEL", "TMP", "KEF"],
    "🏰 Центр Європи":   ["VIE", "PRG", "BUD", "ZRH", "GVA", "MUC", "FRA", "BER"],
    "🌊 Канари":         ["ACE", "TFS", "TFN", "LPA", "FUE"],
    "🇬🇧 Британія":      ["LHR", "LGW", "STN", "MAN", "EDI", "DUB"],
    "🌍 Всюди":          [],  # порожній = без фільтру
}

# Аеропорти для пошуку (вильот)
ORIGIN_CITIES = [
    "WAW", "KRK", "RZE", "WRO", "GDN", "KTW", "POZ",
    "BUD", "PRG", "BTS", "KSC",
    "OTP", "CLJ", "TSR", "IAS", "SCV", "BCM",
    "RMO",
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
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# Зберігаємо налаштування кожного користувача
user_settings = {}   # chat_id -> {budget, region, origins, one_way_only}
watchlist = {}       # chat_id -> [{"origin": "WAW", "destination": "FCO", "threshold": 50}]


def get_airport_name(code: str) -> str:
    return AIRPORT_NAMES.get(code, code)


def ap(code: str) -> str:
    """Форматує код аеропорту з назвою"""
    name = get_airport_name(code)
    if name != code:
        return f"{code} ({name})"
    return code


def get_user_settings(chat_id: int) -> dict:
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "budget": 150,
            "region": "🌍 Всюди",
            "origins": list(ORIGIN_CITIES),
            "one_way": True,
            "return": True,
        }
    return user_settings[chat_id]


# ============================================================
# API ПОШУК
# ============================================================

async def fetch_cheapest_from(session: aiohttp.ClientSession, origin: str,
                               one_way: bool, budget: int, region_filter: list) -> list:
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
                            # Фільтр регіону
                            if region_filter and dest not in region_filter:
                                continue
                            for _, t in tickets.items():
                                price = t.get("price", 0)
                                if price <= 0 or price > budget:
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


async def fetch_all_deals(one_way: bool, budget: int, origins: list, region: str) -> list:
    region_filter = REGIONS.get(region, [])
    all_deals = []
    connector = aiohttp.TCPConnector(limit=10)

    async with aiohttp.ClientSession(connector=connector) as session:
        batch_size = 8
        for i in range(0, len(origins), batch_size):
            batch = origins[i:i + batch_size]
            tasks = [fetch_cheapest_from(session, o, one_way, budget, region_filter) for o in batch]
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
        m = ["січ", "лют", "бер", "квіт", "трав", "черв",
             "лип", "серп", "вер", "жовт", "лист", "груд"]
        return f"{dt.day} {m[dt.month - 1]}"
    except:
        return date_str[:7]


def format_section(deals: list, one_way: bool) -> str:
    trip_type = "oneway" if one_way else "return"
    if one_way:
        msg = "━━━━━━━━━━━━━━━━━━━━\n🛫 *ВАРІАНТ 1 — В ОДИН БІК*\n━━━━━━━━━━━━━━━━━━━━\n\n"
    else:
        msg = "━━━━━━━━━━━━━━━━━━━━\n🔄 *ВАРІАНТ 2 — ТУДИ І НАЗАД (до 7 ночей)*\n━━━━━━━━━━━━━━━━━━━━\n\n"

    if not deals:
        return msg + "😔 Немає даних — спробуй пізніше\n\n"

    count = 0
    for deal in deals:
        if count >= TOP_DEALS_COUNT:
            break
        avg, discount = calc_discount(deal["price"], trip_type)
        dep_date = format_date(deal["departure_at"])
        stops = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
        fire = "🔥🔥🔥" if discount >= 40 else "🔥🔥" if discount >= 20 else "🔥" if discount > 0 else "💰"

        orig_name = ap(deal["origin"])
        dest_name = ap(deal["destination"])

        msg += f"{fire} *{orig_name} → {dest_name}*\n"
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
        msg += f"\n🔗 [Aviasales]({deal['link']})\n\n"
        count += 1
    return msg


async def do_search(chat_id: int) -> str:
    s = get_user_settings(chat_id)
    budget = s["budget"]
    region = s["region"]
    origins = s["origins"]

    tasks = []
    if s["one_way"]:
        tasks.append(fetch_all_deals(True, budget, origins, region))
    if s["return"]:
        tasks.append(fetch_all_deals(False, budget, origins, region))

    results = await asyncio.gather(*tasks)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = f"✈️ *FLIGHT DEALS* — {now}\n"
    msg += f"💶 Бюджет до €{budget} | 🌍 {region}\n\n"

    idx = 0
    if s["one_way"]:
        msg += format_section(results[idx], one_way=True)
        idx += 1
    if s["return"]:
        msg += format_section(results[idx], one_way=False)

    msg += "💡 _Ціни з кешу Aviasales — бронюй швидко!_"
    return msg


# ============================================================
# КЛАВІАТУРИ
# ============================================================

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Шукати deals", callback_data="search")],
        [InlineKeyboardButton(text="💶 Бюджет", callback_data="menu_budget"),
         InlineKeyboardButton(text="🌍 Регіон", callback_data="menu_region")],
        [InlineKeyboardButton(text="🛫 Тип рейсу", callback_data="menu_type"),
         InlineKeyboardButton(text="📍 Аеропорт вильоту", callback_data="menu_origin")],
        [InlineKeyboardButton(text="⭐ Watchlist", callback_data="menu_watchlist")],
    ])


def budget_kb() -> InlineKeyboardMarkup:
    budgets = [30, 50, 75, 100, 150, 200, 300]
    rows = []
    row = []
    for b in budgets:
        row.append(InlineKeyboardButton(text=f"€{b}", callback_data=f"budget_{b}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def region_kb() -> InlineKeyboardMarkup:
    rows = []
    for region in REGIONS.keys():
        rows.append([InlineKeyboardButton(text=region, callback_data=f"region_{region}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def type_kb(chat_id: int) -> InlineKeyboardMarkup:
    s = get_user_settings(chat_id)
    ow = "✅" if s["one_way"] else "☐"
    ret = "✅" if s["return"] else "☐"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{ow} В один бік", callback_data="toggle_oneway")],
        [InlineKeyboardButton(text=f"{ret} Туди-назад", callback_data="toggle_return")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")],
    ])


def origin_kb(page: int = 0) -> InlineKeyboardMarkup:
    """Вибір аеропорту вильоту — по 8 на сторінку"""
    page_size = 8
    total = len(ORIGIN_CITIES)
    start = page * page_size
    end = min(start + page_size, total)

    rows = []
    for code in ORIGIN_CITIES[start:end]:
        name = get_airport_name(code)
        rows.append([InlineKeyboardButton(
            text=f"{code} — {name}",
            callback_data=f"origin_{code}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"origin_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{(total-1)//page_size+1}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"origin_page_{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔄 Всі аеропорти", callback_data="origin_all")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def watchlist_kb(chat_id: int) -> InlineKeyboardMarkup:
    watches = watchlist.get(chat_id, [])
    rows = []
    for i, w in enumerate(watches):
        orig = ap(w["origin"])
        dest = ap(w["destination"])
        rows.append([InlineKeyboardButton(
            text=f"🗑 {w['origin']}→{w['destination']} (€{w['threshold']})",
            callback_data=f"unwatch_{i}"
        )])
    rows.append([InlineKeyboardButton(text="➕ Додати напрямок", callback_data="watch_add")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ============================================================
# ХЕНДЛЕРИ КОМАНД
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    chat_id = message.chat.id
    get_user_settings(chat_id)  # ініціалізуємо
    await message.answer(
        "👋 *Привіт! Я Flight Deals Bot* ✈️\n\n"
        "Знаходжу найдешевші квитки по всій Європі!\n\n"
        "🛫 В один бік\n"
        "🔄 Туди-назад (до 7 ночей)\n"
        "📊 Знижка від середньої ціни\n"
        "⭐ Watchlist — слідкуй за маршрутом\n\n"
        "Використовуй меню нижче 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.message(Command("deals"))
async def cmd_deals(message: Message):
    wait = await message.answer("🔍 Шукаю deals (~30 сек)...")
    msg = await do_search(message.chat.id)
    await wait.delete()
    await message.answer(msg, parse_mode="Markdown",
                         disable_web_page_preview=True,
                         reply_markup=main_menu_kb())


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    s = get_user_settings(message.chat.id)
    await message.answer(
        f"⚙️ *Поточні налаштування:*\n\n"
        f"💶 Бюджет: €{s['budget']}\n"
        f"🌍 Регіон: {s['region']}\n"
        f"🛫 В один бік: {'✅' if s['one_way'] else '❌'}\n"
        f"🔄 Туди-назад: {'✅' if s['return'] else '❌'}\n"
        f"📍 Аеропортів: {len(s['origins'])}",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.message(Command("watch"))
async def cmd_watch(message: Message):
    """Додати до watchlist: /watch WAW FCO 50"""
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "⭐ *Watchlist*\n\n"
            "Формат: `/watch ORIGIN DESTINATION ЦІНА`\n"
            "Приклад: `/watch WAW FCO 50`\n\n"
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

    # Перевіряємо чи вже є
    for w in watchlist[chat_id]:
        if w["origin"] == origin and w["destination"] == destination:
            await message.answer("ℹ️ Цей маршрут вже у watchlist!")
            return

    watchlist[chat_id].append({
        "origin": origin,
        "destination": destination,
        "threshold": threshold
    })

    orig_name = ap(origin)
    dest_name = ap(destination)
    await message.answer(
        f"⭐ Додано до watchlist!\n\n"
        f"*{orig_name} → {dest_name}*\n"
        f"Сповіщу коли ціна буде нижче €{threshold}",
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Flight Deals Bot — команди*\n\n"
        "/start — головне меню\n"
        "/deals — пошук deals зараз\n"
        "/menu — налаштування\n"
        "/watch WAW FCO 50 — watchlist\n"
        "/help — ця довідка\n\n"
        f"🌍 {len(ORIGIN_CITIES)} аеропортів Європи\n"
        "🕘 Авто-розсилка щодня о 9:00",
        parse_mode="Markdown"
    )


# ============================================================
# CALLBACK ХЕНДЛЕРИ (кнопки)
# ============================================================

@dp.callback_query(F.data == "search")
async def cb_search(cb: CallbackQuery):
    await cb.answer()
    wait = await cb.message.answer("🔍 Шукаю deals (~30 сек)...")
    msg = await do_search(cb.message.chat.id)
    await wait.delete()
    await cb.message.answer(msg, parse_mode="Markdown",
                             disable_web_page_preview=True,
                             reply_markup=main_menu_kb())


@dp.callback_query(F.data == "back_main")
async def cb_back(cb: CallbackQuery):
    await cb.answer()
    s = get_user_settings(cb.message.chat.id)
    await cb.message.edit_text(
        f"⚙️ *Налаштування:*\n\n"
        f"💶 Бюджет: €{s['budget']} | 🌍 {s['region']}\n"
        f"🛫 {'✅' if s['one_way'] else '❌'} В один бік | "
        f"🔄 {'✅' if s['return'] else '❌'} Туди-назад",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data == "menu_budget")
async def cb_menu_budget(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "💶 *Вибери максимальний бюджет:*",
        parse_mode="Markdown",
        reply_markup=budget_kb()
    )


@dp.callback_query(F.data.startswith("budget_"))
async def cb_budget(cb: CallbackQuery):
    budget = int(cb.data.split("_")[1])
    chat_id = cb.message.chat.id
    get_user_settings(chat_id)["budget"] = budget
    await cb.answer(f"✅ Бюджет встановлено: €{budget}")
    s = get_user_settings(chat_id)
    await cb.message.edit_text(
        f"✅ Бюджет: *€{budget}*\n\nПоточні налаштування:\n🌍 {s['region']}",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data == "menu_region")
async def cb_menu_region(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "🌍 *Вибери регіон призначення:*",
        parse_mode="Markdown",
        reply_markup=region_kb()
    )


@dp.callback_query(F.data.startswith("region_"))
async def cb_region(cb: CallbackQuery):
    region = cb.data[7:]  # прибираємо "region_"
    chat_id = cb.message.chat.id
    get_user_settings(chat_id)["region"] = region
    await cb.answer(f"✅ Регіон: {region}")
    await cb.message.edit_text(
        f"✅ Регіон встановлено: *{region}*",
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data == "menu_type")
async def cb_menu_type(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "🛫 *Тип рейсу:*",
        parse_mode="Markdown",
        reply_markup=type_kb(cb.message.chat.id)
    )


@dp.callback_query(F.data == "toggle_oneway")
async def cb_toggle_oneway(cb: CallbackQuery):
    s = get_user_settings(cb.message.chat.id)
    s["one_way"] = not s["one_way"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=type_kb(cb.message.chat.id))


@dp.callback_query(F.data == "toggle_return")
async def cb_toggle_return(cb: CallbackQuery):
    s = get_user_settings(cb.message.chat.id)
    s["return"] = not s["return"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=type_kb(cb.message.chat.id))


@dp.callback_query(F.data == "menu_origin")
async def cb_menu_origin(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "📍 *Вибери аеропорт вильоту:*\n_(натисни щоб додати/прибрати)_",
        parse_mode="Markdown",
        reply_markup=origin_kb(0)
    )


@dp.callback_query(F.data.startswith("origin_page_"))
async def cb_origin_page(cb: CallbackQuery):
    page = int(cb.data.split("_")[2])
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=origin_kb(page))


@dp.callback_query(F.data == "origin_all")
async def cb_origin_all(cb: CallbackQuery):
    get_user_settings(cb.message.chat.id)["origins"] = list(ORIGIN_CITIES)
    await cb.answer("✅ Всі аеропорти вибрані!")
    await cb.message.edit_reply_markup(reply_markup=origin_kb(0))


@dp.callback_query(F.data.startswith("origin_") and ~F.data.startswith("origin_page_"))
async def cb_origin_select(cb: CallbackQuery):
    code = cb.data[7:]
    if code == "all":
        return
    s = get_user_settings(cb.message.chat.id)
    if code in s["origins"]:
        if len(s["origins"]) > 1:
            s["origins"].remove(code)
            await cb.answer(f"❌ {ap(code)} прибрано")
        else:
            await cb.answer("⚠️ Має бути хоча б 1 аеропорт!")
    else:
        s["origins"].append(code)
        await cb.answer(f"✅ {ap(code)} додано")


@dp.callback_query(F.data == "menu_watchlist")
async def cb_menu_watchlist(cb: CallbackQuery):
    await cb.answer()
    watches = watchlist.get(cb.message.chat.id, [])
    text = "⭐ *Watchlist*\n\nБот сповістить коли ціна впаде!\n\n"
    if watches:
        for w in watches:
            text += f"• {ap(w['origin'])} → {ap(w['destination'])} — до €{w['threshold']}\n"
    else:
        text += "_Порожньо. Додай командою:_\n`/watch WAW FCO 50`"
    await cb.message.edit_text(text, parse_mode="Markdown",
                                reply_markup=watchlist_kb(cb.message.chat.id))


@dp.callback_query(F.data.startswith("unwatch_"))
async def cb_unwatch(cb: CallbackQuery):
    idx = int(cb.data.split("_")[1])
    chat_id = cb.message.chat.id
    if chat_id in watchlist and idx < len(watchlist[chat_id]):
        removed = watchlist[chat_id].pop(idx)
        await cb.answer(f"🗑 {removed['origin']}→{removed['destination']} видалено")
    await cb.message.edit_reply_markup(reply_markup=watchlist_kb(chat_id))


@dp.callback_query(F.data == "watch_add")
async def cb_watch_add(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(
        "➕ *Додати до Watchlist:*\n\n"
        "Напиши команду:\n`/watch ЗВІДКИ КУДИ ЦІНА`\n\n"
        "Приклад:\n`/watch WAW FCO 50`\n`/watch KRK ATH 40`",
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


# ============================================================
# WATCHLIST ПЕРЕВІРКА
# ============================================================

async def check_watchlist():
    """Перевіряємо watchlist — чи впала ціна"""
    if not watchlist:
        return

    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(connector=connector) as session:
        for chat_id, watches in watchlist.items():
            for w in watches:
                try:
                    params = {
                        "origin": w["origin"],
                        "destination": w["destination"],
                        "currency": "eur",
                        "token": TRAVELPAYOUTS_TOKEN,
                        "one_way": "false",
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
                                            orig_name = ap(w["origin"])
                                            dest_name = ap(w["destination"])
                                            await bot.send_message(
                                                chat_id=chat_id,
                                                text=(
                                                    f"🔔 *WATCHLIST АЛЕРТ!*\n\n"
                                                    f"⭐ *{orig_name} → {dest_name}*\n"
                                                    f"💶 *€{price}* — нижче твого порогу €{w['threshold']}!\n\n"
                                                    f"🔗 [Дивитись на Aviasales](https://www.aviasales.com/search/{w['origin']}{w['destination']})"
                                                ),
                                                parse_mode="Markdown",
                                                disable_web_page_preview=True
                                            )
                except Exception as e:
                    logger.error(f"Watchlist помилка: {e}")
                await asyncio.sleep(0.5)


# ============================================================
# ЩОДЕННА РОЗСИЛКА
# ============================================================

async def send_daily_deals():
    logger.info("Щоденний пошук...")
    all_chats = set(get_user_settings.__defaults__)  # всі chat_id
    for chat_id in list(user_settings.keys()):
        try:
            msg = await do_search(chat_id)
            await bot.send_message(chat_id, msg, parse_mode="Markdown",
                                   disable_web_page_preview=True,
                                   reply_markup=main_menu_kb())
        except Exception as e:
            logger.error(f"Помилка: {e}")


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    # Встановлюємо команди в меню Telegram
    await bot.set_my_commands([
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="deals", description="Шукати deals зараз"),
        BotCommand(command="menu", description="Налаштування"),
        BotCommand(command="watch", description="Watchlist (напр: /watch WAW FCO 50)"),
        BotCommand(command="help", description="Довідка"),
    ])

    scheduler.add_job(send_daily_deals, "cron", hour=9, minute=0)
    scheduler.add_job(check_watchlist, "cron", hour="*/3", minute=0)  # кожні 3 год
    scheduler.start()

    logger.info("Бот v5 запущено! ✈️")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
