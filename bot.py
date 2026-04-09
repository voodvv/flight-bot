import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
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

DEFAULT_BUDGET  = 400   # €
TOP_N           = 5     # скільки deals показувати

# ============================================================
# СЛОВНИК АЕРОПОРТІВ (повний)
# ============================================================
AP = {
    # Польща
    "WAW":"Варшава","KRK":"Краків","RZE":"Жешув","WRO":"Вроцлав",
    "GDN":"Гданськ","KTW":"Катовіце","POZ":"Познань","SZZ":"Щецін",
    "LUZ":"Люблін","BZG":"Бидгощ",
    # Угорщина
    "BUD":"Будапешт","DEB":"Дебрецен",
    # Чехія / Словаччина
    "PRG":"Прага","BRQ":"Брно","BTS":"Братислава","KSC":"Кошіце",
    # Румунія — ВСІ
    "OTP":"Бухарест","BBU":"Бухарест-Бенесе","CLJ":"Клуж-Напока",
    "TSR":"Тімішоара","IAS":"Яси","SCV":"Сучава","BCM":"Бакеу",
    "SBZ":"Сібіу","OMR":"Орадя","SUJ":"Сату-Маре","TGM":"Тирґу-Муреш",
    "CRA":"Крайова","TCE":"Тулча","BAY":"Бая-Маре",
    # Молдова
    "RMO":"Кишинів",
    # Балкани
    "BEG":"Белград","INI":"Ніш","ZAG":"Загреб","SPU":"Спліт",
    "DBV":"Дубровник","ZAD":"Задар","PUY":"Пула","RJK":"Рієка",
    "OSI":"Осієк","SKP":"Скоп'є","OHD":"Охрид","TIA":"Тирана",
    "TGD":"Подгориця","TIV":"Тіват",
    "SOF":"Софія","PDV":"Пловдів","VAR":"Варна","BOJ":"Бургас",
    # Австрія / Швейцарія
    "VIE":"Відень","GRZ":"Грац","INN":"Інсбрук","SZG":"Зальцбург","LNZ":"Лінц",
    "ZRH":"Цюрих","GVA":"Женева","BSL":"Базель",
    # Німеччина
    "MUC":"Мюнхен","FRA":"Франкфурт","BER":"Берлін","HAM":"Гамбург",
    "DUS":"Дюссельдорф","STR":"Штутгарт","CGN":"Кельн","NUE":"Нюрнберг",
    "LEJ":"Лейпциг","DRS":"Дрезден","BRE":"Бремен","FMM":"Меммінген",
    "HHN":"Франкфурт-Хан","DTM":"Дортмунд","PAD":"Падерборн","ERF":"Ерфурт",
    # Франція
    "CDG":"Париж CDG","ORY":"Париж Орлі","LYS":"Ліон","MRS":"Марсель",
    "NCE":"Ніцца","TLS":"Тулуза","BOD":"Бордо","NTE":"Нант",
    "SXB":"Страсбург","MPL":"Монпельє","LIL":"Лілль","BES":"Брест",
    "BIA":"Бастія","AJA":"Аяччо",
    # Велика Британія / Ірландія
    "LHR":"Лондон Хітроу","LGW":"Лондон Гетвік","STN":"Лондон Станстед",
    "LTN":"Лондон Лутон","LCY":"Лондон Сіті","MAN":"Манчестер",
    "BHX":"Бірмінгем","EDI":"Единбург","GLA":"Глазго","BRS":"Брістоль",
    "NCL":"Ньюкасл","LPL":"Ліверпуль","EMA":"Іст-Мідлендс","ABZ":"Абердін",
    "BFS":"Белфаст","DUB":"Дублін","SNN":"Шеннон","ORK":"Корк",
    # Нідерланди / Бельгія / Люксембург
    "AMS":"Амстердам","EIN":"Ейндговен","RTM":"Роттердам","GRQ":"Гронінген",
    "BRU":"Брюссель","CRL":"Брюссель Шарлеруа","LGG":"Льєж","LUX":"Люксембург",
    # Іспанія
    "MAD":"Мадрид","BCN":"Барселона","AGP":"Малага","ALC":"Аліканте",
    "PMI":"Пальма Майорка","IBZ":"Ібіца","VLC":"Валенсія","SVQ":"Севілья",
    "BIO":"Більбао","SDR":"Сантандер","SCQ":"Сантьяго","OVD":"Ов'єдо",
    "VGO":"Віго","GRX":"Гранада","MHN":"Менорка",
    "ACE":"Ланзароте","TFS":"Тенеріфе Пд","TFN":"Тенеріфе Пн",
    "LPA":"Гран Канарія","FUE":"Фуертевентура",
    # Португалія
    "LIS":"Лісабон","OPO":"Порту","FAO":"Фару","FNC":"Мадейра","PDL":"Азори",
    # Скандинавія
    "CPH":"Копенгаген","AAL":"Ольборг","BLL":"Більунд",
    "ARN":"Стокгольм","NYO":"Стокгольм Скавста","GOT":"Гетеборг","MMX":"Мальме",
    "OSL":"Осло","TRF":"Осло Торп","BGO":"Берген","SVG":"Ставангер","TRD":"Тронгейм",
    "HEL":"Гельсінкі","TMP":"Тампере","TKU":"Турку","OUL":"Оулу","RVN":"Рованіємі",
    "KEF":"Рейк'явік",
    # Балтія
    "RIX":"Рига","TLL":"Таллін","VNO":"Вільнюс","KUN":"Каунас","PLQ":"Паланга",
    # Італія
    "FCO":"Рим Фьюмічино","CIA":"Рим Чампіно",
    "MXP":"Мілан Мальпенса","LIN":"Мілан Лінате","BGY":"Мілан Бергамо",
    "VCE":"Венеція","TSF":"Тревізо","NAP":"Неаполь","BRI":"Барі",
    "BLQ":"Болонья","FLR":"Флоренція","PSA":"Піза","VRN":"Верона",
    "TRS":"Трієст","CAG":"Кальярі","OLB":"Ольбія","AHO":"Алгеро",
    "CTA":"Катанія","PMO":"Палермо","PSR":"Пескара","RMI":"Ріміні",
    # Греція / Кіпр / Мальта
    "ATH":"Афіни","SKG":"Салоніки","HER":"Іракліон Крит",
    "CHQ":"Ханья Крит","RHO":"Родос","KGS":"Кос","CFU":"Корфу",
    "ZTH":"Закінф","JMK":"Міконос","JTR":"Санторіні","KLX":"Каламата",
    "LCA":"Ларнака Кіпр","PFO":"Пафос Кіпр","MLA":"Мальта",
    # Туреччина
    "IST":"Стамбул","SAW":"Стамбул Сабіха","AYT":"Анталія",
    "ADB":"Ізмір","ESB":"Анкара","DLM":"Даламан","BJV":"Бодрум",
    # Інше
    "TLV":"Тель-Авів",
    # Часті destination коди без власного аеропорту
    "STO":"Стокгольм (місто)","MIL":"Мілан (місто)","LON":"Лондон (місто)",
    "PAR":"Париж (місто)","ROM":"Рим (місто)","BUH":"Бухарест (місто)",
    "MOW":"Москва","LED":"Санкт-Петербург",
}

def ap(code: str) -> str:
    name = AP.get(code, "")
    return f"{code} ({name})" if name else code

# ============================================================
# РЕГІОНИ
# ============================================================
REGIONS = {
    "🌍 Всюди": [],
    "🇷🇴 Румунія + Молдова": ["OTP","CLJ","TSR","IAS","SCV","BCM","SBZ","OMR","SUJ","TGM","CRA","TCE","RMO"],
    "🏖 Середземномор'я": ["FCO","CIA","MXP","BGY","VCE","NAP","BLQ","FLR","PSA","CTA","PMO",
                           "ATH","SKG","HER","RHO","KGS","CFU","ZTH","JMK","JTR",
                           "LCA","PFO","MLA","PMI","IBZ","AGP","BCN","MAD","AYT","DLM","BJV",
                           "SPU","DBV","TIA","TGD","TIV"],
    "🏔 Балкани":          ["BEG","INI","ZAG","SPU","DBV","SKP","TIA","TGD","TIV","SOF","VAR","BOJ","PDV"],
    "❄️ Скандинавія":     ["CPH","ARN","GOT","OSL","BGO","HEL","TMP","KEF","TLL","RIX","VNO"],
    "🏰 Центр Європи":    ["VIE","PRG","BUD","ZRH","GVA","MUC","FRA","BER","BTS","KSC","BRQ"],
    "🇬🇧 Британія+Ірл":  ["LHR","LGW","STN","LTN","MAN","EDI","GLA","BRS","DUB","ORK"],
    "🌊 Канари":           ["ACE","TFS","TFN","LPA","FUE"],
    "🇵🇹 Іберія":         ["MAD","BCN","AGP","VLC","PMI","LIS","OPO","FAO","SVQ"],
    "🇮🇹 Італія":         ["FCO","CIA","MXP","BGY","VCE","NAP","BLQ","FLR","PSA","VRN","CTA","PMO"],
}

# Аеропорти вильоту
ORIGINS = [
    "WAW","KRK","RZE","WRO","GDN","KTW","POZ",
    "BUD","PRG","BTS","KSC",
    "OTP","CLJ","TSR","IAS","SCV","BCM","SBZ",
    "RMO",
    "VIE","ZRH","GVA","BSL",
    "MUC","FRA","BER","HAM","DUS","STR","CGN","NUE","LEJ","DRS","BRE","FMM","HHN","DTM",
    "CDG","ORY","LYS","MRS","NCE","TLS","BOD","LIL",
    "LHR","LGW","STN","LTN","MAN","EDI","GLA","BRS","DUB",
    "AMS","EIN","BRU","CRL","LUX",
    "FCO","MXP","VCE","NAP","BLQ","PSA","VRN","CTA",
    "MAD","BCN","AGP","VLC","PMI","LIS","OPO",
    "ATH","SKG","HER",
    "CPH","ARN","OSL","HEL",
    "RIX","TLL","VNO",
    "SOF","BEG","ZAG","SPU",
    "IST","SAW",
    "LCA","MLA","TLV",
]

# ============================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot      = Bot(token=TELEGRAM_TOKEN)
dp       = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

user_cfg  : dict[int, dict] = {}
watchlist : dict[int, list] = {}
# Кеш попередніх найкращих цін для детекції нових deals
prev_best : dict[int, dict] = {}
# Кеш реальних середніх цін по маршрутах (заповнюється під час пошуку)
route_avg : dict[str, float] = {}


def cfg(cid: int) -> dict:
    if cid not in user_cfg:
        user_cfg[cid] = {
            "budget": DEFAULT_BUDGET,
            "region": "🌍 Всюди",
            "one_way": True,
            "ret": True,
            "hotel": True,
        }
    return user_cfg[cid]


# ============================================================
# АВІА — кілька endpoint'ів для різноманіття
# ============================================================

async def _api_get(session, url: str, params: dict) -> dict | list | None:
    """Універсальний GET з токеном в обох місцях"""
    params["token"] = TP_TOKEN
    endpoint = url.split("/")[-1]
    try:
        async with session.get(
            url, params=params,
            headers={"x-access-token": TP_TOKEN},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            logger.info(f"API [{endpoint}] origin={params.get('origin','')} → HTTP {r.status}")
            if r.status == 200:
                data = await r.json()
                if isinstance(data, dict):
                    count = len(data.get("data", data) or [])
                    logger.info(f"  → {count} результатів")
                return data
            else:
                text = await r.text()
                logger.warning(f"  → Помилка: {text[:200]}")
    except Exception as e:
        logger.error(f"API [{endpoint}]: {e}")
    return None


async def fetch_origin(session, origin: str, one_way: bool,
                       flight_budget: int, region_codes: list) -> list:
    now   = datetime.now()
    deals = []
    seen  = set()

    def add(dest, price, dep, ret_d, transfers, airline):
        dest = dest.upper() if dest else ""
        if not dest or len(dest) != 3:
            return
        if region_codes and dest not in region_codes:
            return
        if price <= 0 or price > flight_budget:
            return
        key = f"{origin}-{dest}"
        if key in seen:
            return
        seen.add(key)
        nights = None
        if not one_way and ret_d:
            try:
                d1 = datetime.fromisoformat(dep.replace("Z","+00:00"))
                d2 = datetime.fromisoformat(ret_d.replace("Z","+00:00"))
                nights = (d2 - d1).days
                if nights < 1 or nights > 7:
                    return
            except:
                pass
        rk = f"{origin}-{dest}-{'ow' if one_way else 'rt'}"
        route_avg.setdefault(rk, [])
        route_avg[rk].append(price)
        deals.append({
            "origin": origin, "destination": dest,
            "price": price, "airline": airline or "",
            "departure_at": dep or "", "return_at": ret_d or "",
            "transfers": transfers or 0, "nights": nights,
            "link": f"https://www.aviasales.com/search/{origin}{dest}",
        })

    # ── 1. prices/cheap — кілька місяців ──
    for i in range(1, 5):
        month = (now + timedelta(days=30*i)).strftime("%Y-%m")
        params = {"origin": origin, "depart_date": month,
                  "currency": "eur", "one_way": "true" if one_way else "false"}
        if not one_way:
            params["return_date"] = (now + timedelta(days=30*i+5)).strftime("%Y-%m")
        d = await _api_get(session, "https://api.travelpayouts.com/v1/prices/cheap", params)
        if d and d.get("success") and d.get("data"):
            for dest, tickets in d["data"].items():
                for _, t in tickets.items():
                    add(dest, t.get("price",0), t.get("departure_at",""),
                        t.get("return_at",""), t.get("transfers",0), t.get("airline",""))

    # ── 2. prices_for_dates — надійніший endpoint ──
    for i in range(1, 4):
        month = (now + timedelta(days=30*i)).strftime("%Y-%m")
        params = {"origin": origin, "departure_at": month,
                  "currency": "eur", "sorting": "price",
                  "one_way": "true" if one_way else "false",
                  "limit": 30, "unique": "false"}
        if not one_way:
            params["return_at"] = (now + timedelta(days=30*i+5)).strftime("%Y-%m")
        d = await _api_get(session, "https://api.travelpayouts.com/aviasales/v3/prices_for_dates", params)
        if d and d.get("success") and d.get("data"):
            for t in d["data"]:
                add(t.get("destination",""), t.get("price",0),
                    t.get("departure_at",""), t.get("return_at",""),
                    t.get("number_of_changes",0), t.get("airline",""))

    # ── 3. grouped_prices — топ напрямки ──
    params = {"origin": origin, "currency": "eur", "limit": 30,
              "one_way": "true" if one_way else "false",
              "grouping": "DIRECTIONS"}
    d = await _api_get(session, "https://api.travelpayouts.com/aviasales/v3/grouped_prices", params)
    if d and d.get("success") and d.get("data"):
        for item in d["data"]:
            add(item.get("destination",""), item.get("price",0),
                item.get("departure_at",""), item.get("return_at",""),
                item.get("number_of_changes",0), item.get("airline",""))

    # ── 4. special_offers — аномально низькі ──
    d = await _api_get(session,
        "https://api.travelpayouts.com/aviasales/v3/get_special_offers",
        {"origin": origin, "currency": "eur"})
    if d and d.get("success") and d.get("data"):
        for t in d["data"]:
            add(t.get("destination",""), t.get("price",0),
                t.get("departure_at",""), t.get("return_at",""),
                0, t.get("airline",""))

    return deals


async def search_all(one_way: bool, settings: dict) -> list:
    region_codes = REGIONS.get(settings["region"], [])
    flight_budget = (int(settings["budget"] * 0.70)
                     if settings["hotel"] and not one_way
                     else settings["budget"])

    all_deals: list = []
    conn = aiohttp.TCPConnector(limit=15)
    async with aiohttp.ClientSession(connector=conn) as session:
        for i in range(0, len(ORIGINS), 8):
            batch   = ORIGINS[i:i+8]
            tasks   = [fetch_origin(session, o, one_way,
                                    flight_budget, region_codes) for o in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_deals.extend(r)
            await asyncio.sleep(0.4)

    seen = set()
    unique = []
    for d in sorted(all_deals, key=lambda x: x["price"]):
        k = f"{d['origin']}-{d['destination']}"
        if k not in seen:
            seen.add(k)
            unique.append(d)
    return unique


# ============================================================
# ГОТЕЛЬ — Booking.com посилання (надійно, завжди актуально)
# ============================================================

def hotel_booking_link(dest_city: str, check_in: str, check_out: str) -> str:
    city = AP.get(dest_city, dest_city).split()[0]
    return (f"https://www.booking.com/search.html"
            f"?ss={city}&checkin={check_in}&checkout={check_out}"
            f"&group_adults=1&no_rooms=1&order=price")


def hostelworld_link(dest_city: str, check_in: str, check_out: str) -> str:
    city = AP.get(dest_city, dest_city).split()[0]
    return (f"https://www.hostelworld.com/findabed.php"
            f"?ChosenCity={city}&DateFrom={check_in}&DateTo={check_out}")


# ============================================================
# РЕАЛЬНА СЕРЕДНЯ ЦІНА
# ============================================================

def real_avg(origin: str, dest: str, one_way: bool) -> float:
    rk   = f"{origin}-{dest}-{'ow' if one_way else 'rt'}"
    vals = route_avg.get(rk, [])
    if len(vals) >= 2:
        # прибираємо мінімум (поточна ціна) і рахуємо середню решти
        sorted_v = sorted(vals)
        rest = sorted_v[1:] if len(sorted_v) > 1 else sorted_v
        return sum(rest) / len(rest)
    # fallback — середнє по всіх зібраних цінах мінус поточна
    return 165.0 if one_way else 230.0


# ============================================================
# ФОРМАТУВАННЯ
# ============================================================

def fmt_date(s: str) -> str:
    if not s:
        return "?"
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        m  = ["","січ","лют","бер","квіт","трав","черв",
               "лип","серп","вер","жовт","лист","груд"]
        return f"{dt.day} {m[dt.month]}"
    except:
        return s[:7]


def get_check_dates(dep: str, nights: int):
    try:
        d = datetime.fromisoformat(dep.replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d"), (d + timedelta(days=nights)).strftime("%Y-%m-%d")
    except:
        n = datetime.now()
        return n.strftime("%Y-%m-%d"), (n + timedelta(days=3)).strftime("%Y-%m-%d")


async def fmt_deal(deal: dict, one_way: bool, settings: dict) -> str:
    price    = deal["price"]
    avg      = real_avg(deal["origin"], deal["destination"], one_way)
    discount = round((avg - price) / avg * 100) if price < avg else 0
    fire     = "🔥🔥🔥" if discount >= 40 else "🔥🔥" if discount >= 20 else "🔥" if discount > 0 else "💰"
    stops    = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
    dep_d    = fmt_date(deal["departure_at"])

    msg  = f"{fire} *{ap(deal['origin'])} → {ap(deal['destination'])}*\n"
    msg += f"✈️ *€{price:.0f}*"
    if not one_way:
        msg += " туди-назад"
    msg += f" | {stops}"
    if deal["airline"]:
        msg += f" | {deal['airline']}"
    msg += "\n"
    msg += f"📊 Середня ~€{avg:.0f} | "
    msg += f"*дешевше на {discount}%*\n" if discount > 0 else "нова ціна\n"
    msg += f"📅 {dep_d}"

    if not one_way and deal.get("return_at"):
        ret_d = fmt_date(deal["return_at"])
        n_str = f" · {deal['nights']} н." if deal.get("nights") else ""
        msg  += f" — {ret_d}{n_str}"
    msg += "\n"

    # Готель
    if not one_way and settings["hotel"] and deal.get("nights") and deal.get("departure_at"):
        nights   = deal["nights"]
        ci, co   = get_check_dates(deal["departure_at"], nights)
        dest     = deal["destination"]
        max_h    = settings["budget"] - price
        total    = price  # буде оновлено

        # Оціночна ціна готелю (хостел ~15-25€/ніч, готель ~40-80€/ніч)
        est_hostel = round(nights * 18)
        est_hotel  = round(nights * 55)

        bk_link  = hotel_booking_link(dest, ci, co)
        hw_link  = hostelworld_link(dest, ci, co)

        msg += f"🏨 *Проживання {nights} н.:*\n"
        msg += f"  🛏 [Хостел ~€{est_hostel}]({hw_link}) | [Готель ~€{est_hotel}]({bk_link})\n"

        est_total_h = price + est_hostel
        est_total_H = price + est_hotel
        ok_h = "✅" if est_total_h <= settings["budget"] else "⚠️"
        ok_H = "✅" if est_total_H <= settings["budget"] else "⚠️"

        msg += f"💰 Разом хостел *~€{est_total_h}* {ok_h} | готель *~€{est_total_H}* {ok_H}"
        msg += f" / бюджет €{settings['budget']}\n"

    msg += f"🔗 [Aviasales]({deal['link']})\n\n"
    return msg


async def fmt_section(deals: list, one_way: bool, settings: dict) -> str:
    label = "🛫 *В ОДИН БІК*" if one_way else "🔄 *ТУДИ І НАЗАД* (до 7 н.)"
    h_note = " + 🏨" if (not one_way and settings["hotel"]) else ""
    msg  = f"━━━━━━━━━━━━━━━━━━━━\n{label}{h_note}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    if not deals:
        return msg + "😔 Немає даних зараз — спробуй пізніше\n\n"
    count = 0
    for deal in deals:
        if count >= TOP_N:
            break
        msg += await fmt_deal(deal, one_way, settings)
        count += 1
    return msg


async def run_search(chat_id: int) -> str:
    s      = cfg(chat_id)
    tasks  = []
    flags  = []
    if s["one_way"]:
        tasks.append(search_all(True,  s)); flags.append(True)
    if s["ret"]:
        tasks.append(search_all(False, s)); flags.append(False)

    results = await asyncio.gather(*tasks)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    h_status = "✅" if s["hotel"] else "❌"
    msg  = f"✈️ *FLIGHT DEALS* — {now}\n"
    msg += f"💶 Бюджет €{s['budget']} | 🌍 {s['region']} | 🏨 {h_status}\n\n"
    for flag, deals in zip(flags, results):
        msg += await fmt_section(deals, flag, s)
    msg += "💡 _Дані з Aviasales — ціни змінюються швидко!_"

    # Зберігаємо для детекції нових deals
    new_best = {}
    for flag, deals in zip(flags, results):
        k = "ow" if flag else "rt"
        if deals:
            new_best[k] = deals[0]["price"]
    prev_best[chat_id] = new_best

    return msg


# ============================================================
# FLIXBUS — посилання на наступний місяць
# ============================================================

def flixbus_msg() -> str:
    now      = datetime.now()
    nxt      = now.month % 12 + 1
    yr       = now.year + (1 if nxt == 1 else 0)
    first    = f"01.{nxt:02d}.{yr}"
    m_ua     = ["","Січень","Лютий","Березень","Квітень","Травень","Червень",
                "Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"]

    routes = [
        ("Краків","Варшава",      "28","88"),
        ("Краків","Відень",       "28","1"),
        ("Краків","Берлін",       "28","2"),
        ("Краків","Прага",        "28","76"),
        ("Варшава","Берлін",      "88","2"),
        ("Варшава","Прага",       "88","76"),
        ("Варшава","Будапешт",    "88","26"),
        ("Варшава","Відень",      "88","1"),
        ("Будапешт","Відень",     "26","1"),
        ("Будапешт","Братислава", "26","78"),
        ("Будапешт","Загреб",     "26","162"),
        ("Відень","Прага",        "1","76"),
        ("Відень","Братислава",   "1","78"),
        ("Відень","Загреб",       "1","162"),
        ("Прага","Братислава",    "76","78"),
        ("Берлін","Амстердам",    "2","57"),
        ("Берлін","Гамбург",      "2","23"),
        ("Бухарест","Клуж",       "395","393"),
        ("Бухарест","Яси",        "395","396"),
        ("Кишинів","Бухарест",    "400","395"),
        ("Яси","Бухарест",        "396","395"),
        ("Яси","Клуж",            "396","393"),
        ("Белград","Загреб",      "389","162"),
        ("Белград","Будапешт",    "389","26"),
        ("Лісабон","Мадрид",      "45","17"),
        ("Барселона","Мадрид",    "22","17"),
        ("Мілан","Рим",           "7","82"),
        ("Мілан","Флоренція",     "7","96"),
        ("Париж","Ліон",          "13","30"),
        ("Амстердам","Брюссель",  "57","25"),
    ]

    msg  = f"🚌 *FlixBus — {m_ua[nxt]} {yr}*\n"
    msg += f"Найдешевші маршрути на наступний місяць:\n\n"
    for fr, to, fid, tid in routes:
        url = (f"https://shop.global.flixbus.com/s?"
               f"departureCity={fid}&arrivalCity={tid}"
               f"&rideDate={first}&adult=1&currency=EUR")
        msg += f"🚌 [{fr} → {to}]({url})\n"
    msg += f"\n🔍 [Пошук всіх маршрутів FlixBus](https://www.flixbus.com/bus-routes)\n"
    msg += f"\n💡 _Натисни щоб перевірити ціни на {m_ua[nxt]} {yr}_"
    return msg


# ============================================================
# КЛАВІАТУРИ
# ============================================================

def kb_main(cid: int) -> InlineKeyboardMarkup:
    s = cfg(cid)
    h = "🏨 ВКЛ" if s["hotel"] else "🏨 ВИКЛ"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Шукати deals зараз", callback_data="search")],
        [InlineKeyboardButton(text="🚌 FlixBus наступний місяць", callback_data="flixbus")],
        [InlineKeyboardButton(text="💶 Бюджет", callback_data="m_budget"),
         InlineKeyboardButton(text="🌍 Регіон", callback_data="m_region")],
        [InlineKeyboardButton(text=h, callback_data="toggle_hotel"),
         InlineKeyboardButton(text="🛫 Тип рейсу", callback_data="m_type")],
        [InlineKeyboardButton(text="⭐ Watchlist", callback_data="m_watch")],
    ])


def kb_budget() -> InlineKeyboardMarkup:
    bs = [100,150,200,300,400,500]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"€{b}", callback_data=f"b_{b}") for b in bs[:3]],
        [InlineKeyboardButton(text=f"€{b}", callback_data=f"b_{b}") for b in bs[3:]],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


def kb_region() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=r, callback_data=f"r_{i}")]
            for i, r in enumerate(REGIONS)]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_type(cid: int) -> InlineKeyboardMarkup:
    s = cfg(cid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{'✅' if s['one_way'] else '☐'} В один бік",
                              callback_data="tog_ow")],
        [InlineKeyboardButton(text=f"{'✅' if s['ret'] else '☐'} Туди-назад",
                              callback_data="tog_rt")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


def kb_watch(cid: int) -> InlineKeyboardMarkup:
    ws   = watchlist.get(cid, [])
    rows = [[InlineKeyboardButton(
                text=f"🗑 {w['o']}→{w['d']} <€{w['p']}",
                callback_data=f"uw_{i}")]
            for i, w in enumerate(ws)]
    rows.append([InlineKeyboardButton(text="📝 /watch KRK LCA 60", callback_data="noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ============================================================
# ХЕНДЛЕРИ
# ============================================================

@dp.message(Command("start"))
async def on_start(m: Message):
    cfg(m.chat.id)
    await m.answer(
        "👋 *Flight + Hotel Deals Bot* ✈️🏨\n\n"
        f"Пошук по *{len(ORIGINS)} аеропортах Європи*\n"
        "3 джерела даних: cheap prices, special offers, popular directions\n\n"
        "🛫 One-way / 🔄 Return до 7 ночей\n"
        "🏨 Оцінка готелю + посилання (Booking / Hostelworld)\n"
        "📊 Реальна середня ціна маршруту\n"
        "🚌 FlixBus наступний місяць\n"
        "⭐ Watchlist — алерти при зниженні ціни\n"
        "🔔 Авто-сповіщення якщо з'явились нові deals\n\n"
        "👇",
        parse_mode="Markdown",
        reply_markup=kb_main(m.chat.id)
    )


@dp.message(Command("deals"))
async def on_deals(m: Message):
    w = await m.answer("🔍 Шукаю (~40 сек)...")
    txt = await run_search(m.chat.id)
    await w.delete()
    # Розбиваємо якщо > 4096 символів
    for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
        await m.answer(chunk, parse_mode="Markdown",
                       disable_web_page_preview=True,
                       reply_markup=kb_main(m.chat.id))


@dp.message(Command("flixbus"))
async def on_flixbus(m: Message):
    await m.answer(flixbus_msg(), parse_mode="Markdown",
                   disable_web_page_preview=True)


@dp.message(Command("watch"))
async def on_watch(m: Message):
    p = m.text.split()
    if len(p) < 3:
        await m.answer("Формат: `/watch KRK LCA 60`", parse_mode="Markdown")
        return
    o, d = p[1].upper(), p[2].upper()
    threshold = int(p[3]) if len(p) > 3 else 80
    cid = m.chat.id
    watchlist.setdefault(cid, [])
    for w in watchlist[cid]:
        if w["o"] == o and w["d"] == d:
            await m.answer("ℹ️ Вже є у watchlist"); return
    watchlist[cid].append({"o": o, "d": d, "p": threshold})
    await m.answer(f"⭐ Додано: *{ap(o)} → {ap(d)}* < €{threshold}",
                   parse_mode="Markdown")


@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(
        "📋 *Команди:*\n"
        "/start — меню\n/deals — пошук\n"
        "/flixbus — автобуси\n"
        "/watch KRK LCA 60 — watchlist\n/help — довідка",
        parse_mode="Markdown"
    )


# ── Callback ──

@dp.callback_query(F.data == "search")
async def cb_search(cb: CallbackQuery):
    await cb.answer()
    w = await cb.message.answer("🔍 Шукаю (~40 сек)...")
    txt = await run_search(cb.message.chat.id)
    await w.delete()
    for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
        await cb.message.answer(chunk, parse_mode="Markdown",
                                disable_web_page_preview=True,
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "flixbus")
async def cb_flixbus(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(flixbus_msg(), parse_mode="Markdown",
                             disable_web_page_preview=True)


@dp.callback_query(F.data == "back")
async def cb_back(cb: CallbackQuery):
    await cb.answer()
    s = cfg(cb.message.chat.id)
    await cb.message.edit_text(
        f"⚙️ Бюджет: €{s['budget']} | Регіон: {s['region']}\n"
        f"🏨 Готель: {'✅' if s['hotel'] else '❌'} | "
        f"One-way: {'✅' if s['one_way'] else '❌'} | "
        f"Return: {'✅' if s['ret'] else '❌'}",
        reply_markup=kb_main(cb.message.chat.id)
    )


@dp.callback_query(F.data == "m_budget")
async def cb_m_budget(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("💶 Вибери загальний бюджет (квиток + готель):",
                                reply_markup=kb_budget())


@dp.callback_query(F.data.startswith("b_"))
async def cb_budget(cb: CallbackQuery):
    b = int(cb.data[2:])
    cfg(cb.message.chat.id)["budget"] = b
    await cb.answer(f"✅ €{b}")
    await cb.message.edit_text(f"✅ Бюджет: €{b}",
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "m_region")
async def cb_m_region(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🌍 Вибери регіон призначення:",
                                reply_markup=kb_region())


@dp.callback_query(F.data.startswith("r_"))
async def cb_region(cb: CallbackQuery):
    idx = int(cb.data[2:])
    region = list(REGIONS.keys())[idx]
    cfg(cb.message.chat.id)["region"] = region
    await cb.answer(f"✅ {region}")
    await cb.message.edit_text(f"✅ Регіон: {region}",
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "toggle_hotel")
async def cb_toggle_hotel(cb: CallbackQuery):
    s = cfg(cb.message.chat.id)
    s["hotel"] = not s["hotel"]
    status = "увімкнено ✅" if s["hotel"] else "вимкнено ❌"
    await cb.answer(f"🏨 Готель {status}")
    # Перемальовуємо клавіатуру з новим станом
    try:
        await cb.message.edit_reply_markup(reply_markup=kb_main(cb.message.chat.id))
    except:
        await cb.message.answer(f"🏨 Готель {status}",
                                 reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "m_type")
async def cb_m_type(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🛫 Тип рейсу:", reply_markup=kb_type(cb.message.chat.id))


@dp.callback_query(F.data == "tog_ow")
async def cb_tog_ow(cb: CallbackQuery):
    s = cfg(cb.message.chat.id)
    s["one_way"] = not s["one_way"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=kb_type(cb.message.chat.id))


@dp.callback_query(F.data == "tog_rt")
async def cb_tog_rt(cb: CallbackQuery):
    s = cfg(cb.message.chat.id)
    s["ret"] = not s["ret"]
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=kb_type(cb.message.chat.id))


@dp.callback_query(F.data == "m_watch")
async def cb_m_watch(cb: CallbackQuery):
    await cb.answer()
    ws  = watchlist.get(cb.message.chat.id, [])
    txt = "⭐ *Watchlist*\n\n"
    txt += "\n".join(f"• {ap(w['o'])} → {ap(w['d'])} < €{w['p']}" for w in ws) if ws \
           else "_Порожньо._\nДодай: `/watch KRK LCA 60`"
    await cb.message.edit_text(txt, parse_mode="Markdown",
                                reply_markup=kb_watch(cb.message.chat.id))


@dp.callback_query(F.data.startswith("uw_"))
async def cb_uw(cb: CallbackQuery):
    i = int(cb.data[3:])
    cid = cb.message.chat.id
    if cid in watchlist and i < len(watchlist[cid]):
        watchlist[cid].pop(i)
    await cb.answer("🗑 Видалено")
    await cb.message.edit_reply_markup(reply_markup=kb_watch(cid))


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery): await cb.answer()


# ============================================================
# ФОНОВІ ЗАДАЧІ
# ============================================================

async def daily_deals():
    for cid in list(user_cfg):
        try:
            txt = await run_search(cid)
            for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
                await bot.send_message(cid, chunk, parse_mode="Markdown",
                                       disable_web_page_preview=True,
                                       reply_markup=kb_main(cid))
        except Exception as e:
            logger.error(f"daily: {e}")


async def check_watchlist():
    for cid, watches in list(watchlist.items()):
        for w in watches:
            try:
                async with aiohttp.ClientSession() as session:
                    month = datetime.now().strftime("%Y-%m")
                    d = await _api_get(session,
                        "https://api.travelpayouts.com/aviasales/v3/prices_for_dates",
                        {"origin": w["o"], "destination": w["d"],
                         "departure_at": month, "currency": "eur",
                         "one_way": "true", "sorting": "price", "limit": 5})
                    if d and d.get("success") and d.get("data"):
                        for t in d["data"]:
                            p = t.get("price", 0)
                            if 0 < p <= w["p"]:
                                await bot.send_message(
                                    cid,
                                    f"🔔 *WATCHLIST АЛЕРТ!*\n"
                                    f"*{ap(w['o'])} → {ap(w['d'])}*\n"
                                    f"💶 *€{p}* (поріг €{w['p']})\n"
                                    f"🔗 [Aviasales](https://www.aviasales.com/search/{w['o']}{w['d']})",
                                    parse_mode="Markdown",
                                    disable_web_page_preview=True
                                )
                                break
            except Exception as e:
                logger.error(f"watch: {e}")
            await asyncio.sleep(0.3)


async def check_new_deals():
    """Сповіщаємо якщо ціна впала більш ніж на 15% від попереднього пошуку"""
    for cid in list(user_cfg):
        try:
            s      = cfg(cid)
            tasks  = []
            flags  = []
            if s["one_way"]: tasks.append(search_all(True,  s)); flags.append("ow")
            if s["ret"]:     tasks.append(search_all(False, s)); flags.append("rt")
            results = await asyncio.gather(*tasks)

            new_best = {}
            for flag, deals in zip(flags, results):
                if deals:
                    new_best[flag] = deals[0]["price"]

            prev = prev_best.get(cid, {})
            alerts = []
            for flag, price in new_best.items():
                if flag in prev and price < prev[flag] * 0.85:
                    label = "one-way" if flag == "ow" else "туди-назад"
                    alerts.append(
                        f"📉 *{label}*: нова низька ціна *€{price:.0f}* "
                        f"(була €{prev[flag]:.0f}, -{round((1-price/prev[flag])*100)}%)"
                    )
            prev_best[cid] = new_best

            if alerts:
                await bot.send_message(
                    cid,
                    "🔔 *НОВІ DEALS З'ЯВИЛИСЬ!*\n\n" + "\n".join(alerts) +
                    "\n\nНатисни /deals щоб переглянути!",
                    parse_mode="Markdown",
                    reply_markup=kb_main(cid)
                )
        except Exception as e:
            logger.error(f"new_deals: {e}")


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    await bot.set_my_commands([
        BotCommand(command="start",   description="Головне меню"),
        BotCommand(command="deals",   description="Пошук deals"),
        BotCommand(command="flixbus", description="FlixBus наступний місяць"),
        BotCommand(command="watch",   description="/watch KRK LCA 60"),
        BotCommand(command="help",    description="Довідка"),
    ])
    scheduler.add_job(daily_deals,      "cron", hour=9,     minute=0)
    scheduler.add_job(check_watchlist,  "cron", hour="*/3", minute=30)
    scheduler.add_job(check_new_deals,  "cron", hour="*/6", minute=0)
    scheduler.start()
    logger.info("Bot v7 ✈️🏨🚌")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
