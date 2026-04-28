"""
Flight Deals Bot v8
- Авто-пошук deals по всій Європі + екзотика
- Режим "один аеропорт" (IAS → всюди → IAS)
- Готель в пакеті (Booking + Hostelworld посилання)
- FlixBus наступний місяць
- Watchlist з алертами
- Авто-сповіщення нових deals кожні 6 год
- Реальна середня ціна по маршруту
"""

import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
)
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ════════════════════════════════════════════════
# НАЛАШТУВАННЯ — вписати свої ключі
# ════════════════════════════════════════════════
TELEGRAM_TOKEN = "AAFhZMfMNCcTv-yXTDB1mouUFaOBrO_Jac8"
TRAVELPAYOUTS_TOKEN = "83ab9d18d7fb0092294828b8104b50a5"

DEFAULT_BUDGET = 400
TOP_N          = 5

# ════════════════════════════════════════════════
# АЕРОПОРТИ
# ════════════════════════════════════════════════
AIRPORTS = {
    # ── Найближчі до України ──
    "WAW": "Варшава, Польща",
    "KRK": "Краків, Польща",
    "RZE": "Жешув, Польща",
    "WRO": "Вроцлав, Польща",
    "GDN": "Гданськ, Польща",
    "KTW": "Катовіце, Польща",
    "POZ": "Познань, Польща",
    "LUZ": "Люблін, Польща",
    "BUD": "Будапешт, Угорщина",
    "DEB": "Дебрецен, Угорщина",
    "PRG": "Прага, Чехія",
    "BRQ": "Брно, Чехія",
    "BTS": "Братислава, Словаччина",
    "KSC": "Кошіце, Словаччина",
    # ── Румунія — всі ──
    "OTP": "Бухарест, Румунія",
    "CLJ": "Клуж-Напока, Румунія",
    "TSR": "Тімішоара, Румунія",
    "IAS": "Яси, Румунія",
    "SCV": "Сучава, Румунія",
    "BCM": "Бакеу, Румунія",
    "SBZ": "Сібіу, Румунія",
    "OMR": "Орадя, Румунія",
    "SUJ": "Сату-Маре, Румунія",
    "TGM": "Тирґу-Муреш, Румунія",
    "CRA": "Крайова, Румунія",
    "TCE": "Тулча, Румунія",
    # ── Молдова ──
    "RMO": "Кишинів, Молдова",
    # ── Балкани ──
    "BEG": "Белград, Сербія",
    "INI": "Ніш, Сербія",
    "ZAG": "Загреб, Хорватія",
    "SPU": "Спліт, Хорватія",
    "DBV": "Дубровник, Хорватія",
    "ZAD": "Задар, Хорватія",
    "PUY": "Пула, Хорватія",
    "SKP": "Скоп'є, Македонія",
    "TIA": "Тирана, Албанія",
    "TGD": "Подгориця, Чорногорія",
    "TIV": "Тіват, Чорногорія",
    "SOF": "Софія, Болгарія",
    "VAR": "Варна, Болгарія",
    "BOJ": "Бургас, Болгарія",
    "PDV": "Пловдів, Болгарія",
    # ── Центральна Європа ──
    "VIE": "Відень, Австрія",
    "GRZ": "Грац, Австрія",
    "SZG": "Зальцбург, Австрія",
    "INN": "Інсбрук, Австрія",
    "ZRH": "Цюрих, Швейцарія",
    "GVA": "Женева, Швейцарія",
    "BSL": "Базель, Швейцарія",
    # ── Німеччина ──
    "MUC": "Мюнхен, Німеччина",
    "FRA": "Франкфурт, Німеччина",
    "BER": "Берлін, Німеччина",
    "HAM": "Гамбург, Німеччина",
    "DUS": "Дюссельдорф, Німеччина",
    "STR": "Штутгарт, Німеччина",
    "CGN": "Кельн, Німеччина",
    "NUE": "Нюрнберг, Німеччина",
    "LEJ": "Лейпциг, Німеччина",
    "DRS": "Дрезден, Німеччина",
    "BRE": "Бремен, Німеччина",
    "FMM": "Меммінген, Німеччина",
    "HHN": "Франкфурт-Хан, Німеччина",
    "DTM": "Дортмунд, Німеччина",
    # ── Франція ──
    "CDG": "Париж CDG, Франція",
    "ORY": "Париж Орлі, Франція",
    "LYS": "Ліон, Франція",
    "MRS": "Марсель, Франція",
    "NCE": "Ніцца, Франція",
    "TLS": "Тулуза, Франція",
    "BOD": "Бордо, Франція",
    "NTE": "Нант, Франція",
    "SXB": "Страсбург, Франція",
    "LIL": "Лілль, Франція",
    # ── Британія + Ірландія ──
    "LHR": "Лондон Хітроу, Британія",
    "LGW": "Лондон Гетвік, Британія",
    "STN": "Лондон Станстед, Британія",
    "LTN": "Лондон Лутон, Британія",
    "MAN": "Манчестер, Британія",
    "BHX": "Бірмінгем, Британія",
    "EDI": "Единбург, Британія",
    "GLA": "Глазго, Британія",
    "BRS": "Брістоль, Британія",
    "DUB": "Дублін, Ірландія",
    "ORK": "Корк, Ірландія",
    # ── Нідерланди / Бельгія / Люкс ──
    "AMS": "Амстердам, Нідерланди",
    "EIN": "Ейндговен, Нідерланди",
    "BRU": "Брюссель, Бельгія",
    "CRL": "Брюссель-Шарлеруа, Бельгія",
    "LUX": "Люксембург",
    # ── Іспанія ──
    "MAD": "Мадрид, Іспанія",
    "BCN": "Барселона, Іспанія",
    "AGP": "Малага, Іспанія",
    "ALC": "Аліканте, Іспанія",
    "PMI": "Пальма Майорка, Іспанія",
    "IBZ": "Ібіца, Іспанія",
    "VLC": "Валенсія, Іспанія",
    "SVQ": "Севілья, Іспанія",
    "BIO": "Більбао, Іспанія",
    "ACE": "Ланзароте, Канари",
    "TFS": "Тенеріфе Пд, Канари",
    "TFN": "Тенеріфе Пн, Канари",
    "LPA": "Гран Канарія, Канари",
    "FUE": "Фуертевентура, Канари",
    "GMZ": "Ла Гомера, Канари",
    # ── Португалія + острови ──
    "LIS": "Лісабон, Португалія",
    "OPO": "Порту, Португалія",
    "FAO": "Фару, Португалія",
    "FNC": "Фуншал Мадейра, Португалія",  # ← Мадейра!
    "PDL": "Понта-Делгада Азори, Португалія",
    "TER": "Терсейра Азори, Португалія",
    # ── Скандинавія ──
    "CPH": "Копенгаген, Данія",
    "BLL": "Більунд, Данія",
    "ARN": "Стокгольм, Швеція",
    "NYO": "Стокгольм-Скавста, Швеція",
    "GOT": "Гетеборг, Швеція",
    "MMX": "Мальме, Швеція",
    "OSL": "Осло, Норвегія",
    "BGO": "Берген, Норвегія",
    "SVG": "Ставангер, Норвегія",
    "HEL": "Гельсінкі, Фінляндія",
    "TMP": "Тампере, Фінляндія",
    "RVN": "Рованіємі, Фінляндія",  # ← Санта Клаус!
    "KEF": "Рейк'явік, Ісландія",
    # ── Балтія ──
    "RIX": "Рига, Латвія",
    "TLL": "Таллін, Естонія",
    "VNO": "Вільнюс, Литва",
    "KUN": "Каунас, Литва",
    # ── Італія ──
    "FCO": "Рим Фьюмічино, Італія",
    "CIA": "Рим Чампіно, Італія",
    "MXP": "Мілан Мальпенса, Італія",
    "BGY": "Мілан Бергамо, Італія",
    "VCE": "Венеція, Італія",
    "TSF": "Тревізо, Італія",
    "NAP": "Неаполь, Італія",
    "BRI": "Барі, Італія",
    "BLQ": "Болонья, Італія",
    "FLR": "Флоренція, Італія",
    "PSA": "Піза, Італія",
    "VRN": "Верона, Італія",
    "CAG": "Кальярі Сардинія, Італія",
    "OLB": "Ольбія Сардинія, Італія",
    "CTA": "Катанія Сицилія, Італія",
    "PMO": "Палермо Сицилія, Італія",
    # ── Греція + острови ──
    "ATH": "Афіни, Греція",
    "SKG": "Салоніки, Греція",
    "HER": "Іракліон Крит, Греція",
    "CHQ": "Ханья Крит, Греція",
    "RHO": "Родос, Греція",
    "KGS": "Кос, Греція",
    "CFU": "Корфу, Греція",
    "ZTH": "Закінф, Греція",
    "JMK": "Міконос, Греція",
    "JTR": "Санторіні, Греція",
    "KLX": "Каламата, Греція",
    "SMI": "Самос, Греція",
    "MJT": "Мітіліні Лесбос, Греція",
    # ── Кіпр + Мальта ──
    "LCA": "Ларнака, Кіпр",
    "PFO": "Пафос, Кіпр",
    "MLA": "Мальта",
    # ── Туреччина ──
    "IST": "Стамбул, Туреччина",
    "SAW": "Стамбул-Сабіха, Туреччина",
    "AYT": "Анталія, Туреччина",
    "ADB": "Ізмір, Туреччина",
    "DLM": "Даламан, Туреччина",
    "BJV": "Бодрум, Туреччина",
    "GZT": "Газіантеп, Туреччина",
    "TZX": "Трабзон, Туреччина",
    # ── Близький Схід ──
    "TLV": "Тель-Авів, Ізраїль",
    "AMM": "Амман, Йорданія",
    "BEY": "Бейрут, Ліван",
    "DXB": "Дубай, ОАЕ",
    "AUH": "Абу-Дабі, ОАЕ",
    "DOH": "Доха, Катар",
    "KWI": "Кувейт",
    # ── Африка ──
    "CMN": "Касабланка, Марокко",
    "RAK": "Марракеш, Марокко",
    "TNG": "Танжер, Марокко",
    "AGA": "Агадір, Марокко",
    "TUN": "Туніс, Туніс",
    "DJE": "Джерба, Туніс",
    "CAI": "Каїр, Єгипет",
    "HRG": "Хургада, Єгипет",
    "SSH": "Шарм-ель-Шейх, Єгипет",
    "LXR": "Луксор, Єгипет",
    "JNB": "Йоганнесбург, ПАР",
    "CPT": "Кейптаун, ПАР",
    "NBO": "Найробі, Кенія",
    "MBA": "Момбаса, Кенія",
    "ZNZ": "Занзібар, Танзанія",  # ← Екзотика!
    "DAR": "Дар-ес-Салам, Танзанія",
    "ADD": "Аддис-Абеба, Ефіопія",
    "LOS": "Лагос, Нігерія",
    "ABV": "Абуджа, Нігерія",
    "ACC": "Аккра, Гана",
    "DKR": "Дакар, Сенегал",
    "RUN": "Реюньйон, Франція",  # ← Острів!
    "MRU": "Маврикій",          # ← Рай!
    "SEZ": "Сейшели",           # ← Мрія!
    "TNR": "Антананаріву, Мадагаскар",
    # ── Азія ──
    "BKK": "Бангкок, Таїланд",
    "HKT": "Пхукет, Таїланд",
    "CNX": "Чіанг Маї, Таїланд",
    "KBV": "Крабі, Таїланд",
    "USM": "Ко Самуї, Таїланд",
    "DPS": "Балі, Індонезія",    # ← Балі!
    "CGK": "Джакарта, Індонезія",
    "KUL": "Куала-Лумпур, Малайзія",
    "PEN": "Пенанг, Малайзія",
    "SIN": "Сінгапур",
    "MNL": "Маніла, Філіппіни",
    "CEB": "Себу, Філіппіни",
    "SGN": "Хошимін, В'єтнам",
    "HAN": "Ханой, В'єтнам",
    "DAD": "Дананг, В'єтнам",
    "REP": "Сіємреап Ангкор, Камбоджа",
    "PNH": "Пномпень, Камбоджа",
    "RGN": "Янгон, М'янма",
    "DEL": "Делі, Індія",
    "BOM": "Мумбаї, Індія",
    "GOI": "Гоа, Індія",         # ← Гоа!
    "MAA": "Ченнаї, Індія",
    "COK": "Кочін, Індія",
    "CMB": "Коломбо, Шрі-Ланка",
    "MLE": "Мале, Мальдіви",     # ← Мальдіви!
    "KTM": "Катманду, Непал",
    "PEK": "Пекін, Китай",
    "PVG": "Шанхай, Китай",
    "CAN": "Гуанчжоу, Китай",
    "HKG": "Гонконг",
    "NRT": "Токіо Нарита, Японія",
    "HND": "Токіо Ханеда, Японія",
    "KIX": "Осака, Японія",
    "ICN": "Сеул, Корея",
    "TPE": "Тайпей, Тайвань",
    # ── Америка ──
    "JFK": "Нью-Йорк, США",
    "EWR": "Нью-Йорк Ньюарк, США",
    "LAX": "Лос-Анджелес, США",
    "MIA": "Маямі, США",
    "BOS": "Бостон, США",
    "ORD": "Чикаго, США",
    "YYZ": "Торонто, Канада",
    "YVR": "Ванкувер, Канада",
    "YUL": "Монреаль, Канада",
    "GRU": "Сан-Паулу, Бразилія",
    "GIG": "Ріо-де-Жанейро, Бразилія",
    "EZE": "Буенос-Айрес, Аргентина",
    "LIM": "Ліма, Перу",
    "BOG": "Богота, Колумбія",
    "CUN": "Канкун, Мексика",
    "MEX": "Мехіко, Мексика",
    "HAV": "Гавана, Куба",
    "SJO": "Сан-Хосе, Коста-Ріка",
    # ── Океанія ──
    "SYD": "Сідней, Австралія",
    "MEL": "Мельбурн, Австралія",
    "BNE": "Брісбен, Австралія",
    "AKL": "Окленд, Нова Зеландія",
    "NAN": "Нанді, Фіджі",
    "PPT": "Папеєте, Таїті",     # ← Таїті!
    "FAA": "Папеєте Фаа'а, Поліне́зія",
    # ── Додаткові острови / екзотика ──
    "GPA": "Патра, Греція",
    "HRE": "Гарare, Зімбабве",
    "SZB": "Куала-Лумпур Субанг",
    "FNC_": "Мадейра",
    "SID": "Острів Сал, Кабо-Верде",  # ← Кабо-Верде!
    "RAI": "Прая, Кабо-Верде",
    "BVC": "Боа-Віста, Кабо-Верде",
    "VXE": "Сан-Вісенте, Кабо-Верде",
}

# Аеропорти для авто-пошуку (тільки ті що мають достатньо рейсів)
SEARCH_ORIGINS = [
    "WAW","KRK","RZE","WRO","GDN","KTW","POZ",
    "BUD","PRG","BTS","KSC",
    "OTP","CLJ","TSR","IAS","SCV","BCM",
    "RMO",
    "VIE","ZRH","GVA",
    "MUC","FRA","BER","HAM","DUS","STR","CGN","NUE","BRE","FMM","HHN","DTM",
    "CDG","ORY","LYS","MRS","NCE","TLS","BOD","LIL",
    "LHR","LGW","STN","LTN","MAN","EDI","GLA","BRS","DUB",
    "AMS","EIN","BRU","CRL","LUX",
    "FCO","MXP","BGY","VCE","NAP","BLQ","PSA","VRN","CTA",
    "MAD","BCN","AGP","VLC","PMI","LIS","OPO","FAO","FNC",
    "ATH","SKG","HER","RHO","CFU",
    "CPH","ARN","OSL","HEL",
    "RIX","TLL","VNO",
    "SOF","BEG","ZAG","SPU","TIA",
    "IST","SAW","AYT",
    "LCA","PFO","MLA","TLV",
    # Деякі далекі для різноманіття
    "DXB","DOH","CMN","RAK","BKK","DPS",
]

REGIONS = {
    "🌍 Всюди":            [],
    "🇷🇴 Румунія+Молдова": ["OTP","CLJ","TSR","IAS","SCV","BCM","SBZ","OMR","CRA","TCE","RMO"],
    "🏖 Середземномор'я":  ["FCO","CIA","MXP","BGY","VCE","NAP","BLQ","FLR","PSA","CTA","PMO",
                             "ATH","SKG","HER","RHO","KGS","CFU","ZTH","JMK","JTR",
                             "LCA","PFO","MLA","PMI","IBZ","AGP","BCN","AYT","DLM","BJV",
                             "SPU","DBV","TIA","TGD","TIV","TUN","DJE"],
    "🏔 Балкани":          ["BEG","INI","ZAG","SPU","DBV","SKP","TIA","TGD","TIV","SOF","VAR","BOJ"],
    "❄️ Скандинавія":     ["CPH","ARN","GOT","OSL","BGO","HEL","TMP","KEF","RVN"],
    "🏰 Центр Європи":    ["VIE","PRG","BUD","ZRH","GVA","MUC","FRA","BER","BTS","BRQ"],
    "🇬🇧 Британія+Ірл":  ["LHR","LGW","STN","LTN","MAN","EDI","GLA","DUB","ORK"],
    "🌊 Атлантика":        ["FNC","PDL","TER","ACE","TFS","LPA","FUE","SID","RAI","BVC"],
    "🌍 Африка+Єгипет":   ["CMN","RAK","TUN","DJE","CAI","HRG","SSH","LXR","ZNZ","MRU","SEZ"],
    "✈️ Далеко/Азія":     ["DXB","AUH","DOH","BKK","HKT","DPS","SIN","KUL","DEL","GOI","MLE"],
    "🌎 Америка":          ["JFK","LAX","MIA","GRU","CUN","MEX","YYZ"],
}

# ════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

bot       = Bot(token=TELEGRAM_TOKEN)
dp        = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler(timezone="Europe/Bucharest")

user_cfg  : dict[int, dict] = {}
watchlist : dict[int, list] = {}
prev_best : dict[int, dict] = {}
route_prices: dict[str, list] = {}   # накопичуємо ціни для реальної середньої


def cfg(cid: int) -> dict:
    if cid not in user_cfg:
        user_cfg[cid] = {
            "budget":   DEFAULT_BUDGET,
            "region":   "🌍 Всюди",
            "one_way":  True,
            "ret":      True,
            "hotel":    True,
            "origin":   None,    # None = всі аеропорти, інакше конкретний
        }
    return user_cfg[cid]


def ap(code: str) -> str:
    name = AIRPORTS.get(code, "")
    return f"{code} ({name})" if name else code


def city_name(code: str) -> str:
    """Тільки місто без країни"""
    full = AIRPORTS.get(code, code)
    return full.split(",")[0].strip()


# ════════════════════════════════════════════════
# API
# ════════════════════════════════════════════════

async def api_get(session: aiohttp.ClientSession, url: str, params: dict):
    params = dict(params)
    params["token"] = TP_TOKEN
    try:
        async with session.get(
            url, params=params,
            headers={"x-access-token": TP_TOKEN},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            ep = url.split("/")[-1]
            log.info(f"[{ep}] {params.get('origin','')} HTTP {r.status}")
            if r.status == 200:
                data = await r.json()
                return data
            log.warning(f"[{ep}] Error: {await r.text()[:150]}")
    except Exception as e:
        log.error(f"api_get {url}: {e}")
    return None


async def fetch_from_origin(
    session, origin: str, one_way: bool,
    max_price: int, region_codes: list
) -> list:
    now   = datetime.now()
    deals = []
    seen  = set()

    def add(dest, price, dep, ret_d, stops, airline):
        if not dest or len(dest) != 3:
            return
        dest = dest.upper()
        if region_codes and dest not in region_codes:
            return
        if price <= 0 or price > max_price:
            return
        key = f"{origin}-{dest}"
        if key in seen:
            return
        seen.add(key)
        nights = None
        if not one_way and ret_d:
            try:
                d1 = datetime.fromisoformat(dep.replace("Z", "+00:00"))
                d2 = datetime.fromisoformat(ret_d.replace("Z", "+00:00"))
                nights = (d2 - d1).days
                if nights < 1 or nights > 7:
                    return
            except:
                pass
        rk = f"{origin}-{dest}-{'ow' if one_way else 'rt'}"
        route_prices.setdefault(rk, []).append(price)
        deals.append({
            "origin": origin, "destination": dest,
            "price": price, "airline": airline or "",
            "departure_at": dep or "", "return_at": ret_d or "",
            "transfers": stops or 0, "nights": nights,
            "link": f"https://www.aviasales.com/search/{origin}{dest}",
        })

    # ── 1. GraphQL API — найнадійніше, реальні дані ──
    for i in range(1, 4):
        month = (now + timedelta(days=30*i)).strftime("%Y-%m-01")
        if one_way:
            query = """{ prices_one_way(
                params: { origin: "%s" depart_months: "%s" }
                paging: { limit: 30 offset: 0 }
                sorting: VALUE_ASC
            ) { departure_at value trip_duration ticket_link destination { iata } airline { iata } } }""" % (origin, month)
        else:
            query = """{ prices_round_trip(
                params: { origin: "%s" depart_months: "%s" min_trip_duration: 1 max_trip_duration: 7 }
                paging: { limit: 30 offset: 0 }
                sorting: VALUE_ASC
            ) { departure_at return_at value trip_duration ticket_link destination { iata } airline { iata } } }""" % (origin, month)
        try:
            async with session.post(
                "https://api.travelpayouts.com/graphql/v1/query",
                json={"query": query},
                headers={"X-Access-Token": TP_TOKEN, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:
                log.info(f"[GraphQL] {origin} {'OW' if one_way else 'RT'} m+{i} HTTP {r.status}")
                if r.status == 200:
                    d = await r.json()
                    key_name = "prices_one_way" if one_way else "prices_round_trip"
                    tickets = (d.get("data") or {}).get(key_name) or []
                    log.info(f"  → {len(tickets)} результатів")
                    for t in tickets:
                        price = t.get("value", 0)
                        dest  = (t.get("destination") or {}).get("iata", "")
                        air   = (t.get("airline") or {}).get("iata", "")
                        dep   = t.get("departure_at", "")
                        ret   = t.get("return_at", "") if not one_way else ""
                        add(dest, price, dep, ret, 0, air)
        except Exception as e:
            log.error(f"GraphQL {origin}: {e}")

    # ── 2. /v2/prices/latest — без origin/dest = топ-30 дешевих ──
    # (запускаємо тільки один раз для origin)
    d = await api_get(session,
        "https://api.travelpayouts.com/v2/prices/latest",
        {"origin": origin, "currency": "eur", "period_type": "year",
         "page": 1, "limit": 30, "sorting": "price", "trip_class": 0,
         "one_way": "true" if one_way else "false",
         "show_to_affiliates": "false"})
    if d and d.get("success") and d.get("data"):
        for t in d["data"]:
            add(t.get("destination",""), t.get("value",0),
                t.get("depart_date",""), t.get("return_date",""),
                t.get("number_of_changes",0), "")

    # ── 3. /v1/prices/cheap — класичний кеш, всі ринки ──
    for market in ["ua", "pl", "ro", "en", "de", "fr"]:
        for i in range(1, 4):
            month = (now + timedelta(days=30*i)).strftime("%Y-%m")
            p = {"origin": origin, "depart_date": month, "currency": "eur",
                 "one_way": "true" if one_way else "false", "market": market}
            if not one_way:
                p["return_date"] = (now + timedelta(days=30*i+4)).strftime("%Y-%m")
            d = await api_get(session,
                "https://api.travelpayouts.com/v1/prices/cheap", p)
            if d and d.get("success") and d.get("data"):
                for dest, tickets in d["data"].items():
                    for _, t in tickets.items():
                        add(dest, t.get("price",0), t.get("departure_at",""),
                            t.get("return_at",""), t.get("transfers",0), t.get("airline",""))

    # ── 4. /v1/prices/monthly — ціни по місяцях ──
    d = await api_get(session,
        "https://api.travelpayouts.com/v1/prices/monthly",
        {"origin": origin, "currency": "eur",
         "one_way": "true" if one_way else "false"})
    if d and d.get("success") and d.get("data"):
        for dest, months_data in d["data"].items():
            for month_key, t in months_data.items():
                add(dest, t.get("price",0), t.get("departure_at",""),
                    t.get("return_at",""), t.get("transfers",0), t.get("airline",""))

    # ── 5. get_special_offers — аномально дешеві ──
    d = await api_get(session,
        "https://api.travelpayouts.com/aviasales/v3/get_special_offers",
        {"origin": origin, "currency": "eur"})
    if d and d.get("success") and d.get("data"):
        for t in d["data"]:
            add(t.get("destination",""), t.get("price",0),
                t.get("departure_at",""), t.get("return_at",""),
                0, t.get("airline",""))

    return deals


async def search_deals(one_way: bool, settings: dict) -> list:
    region_codes = REGIONS.get(settings["region"], [])
    max_price = (int(settings["budget"] * 0.70)
                 if settings["hotel"] and not one_way
                 else settings["budget"])

    # Якщо вибраний конкретний аеропорт — шукаємо тільки з нього
    origins = ([settings["origin"]] if settings.get("origin")
               else SEARCH_ORIGINS)

    all_deals = []
    conn = aiohttp.TCPConnector(limit=15)
    async with aiohttp.ClientSession(connector=conn) as session:
        for i in range(0, len(origins), 8):
            batch = origins[i:i+8]
            tasks = [fetch_from_origin(session, o, one_way, max_price, region_codes)
                     for o in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_deals.extend(r)
            await asyncio.sleep(0.3)

    # Дедуплікація + сортування за ціною
    seen, unique = set(), []
    for d in sorted(all_deals, key=lambda x: x["price"]):
        k = f"{d['origin']}-{d['destination']}"
        if k not in seen:
            seen.add(k)
            unique.append(d)
    return unique


def avg_price(origin: str, dest: str, one_way: bool) -> float:
    rk   = f"{origin}-{dest}-{'ow' if one_way else 'rt'}"
    vals = route_prices.get(rk, [])
    if len(vals) >= 3:
        sv = sorted(vals)
        rest = sv[1:]  # прибираємо найдешевший (поточний)
        return round(sum(rest) / len(rest))
    return 160 if one_way else 250


# ════════════════════════════════════════════════
# ФОРМАТУВАННЯ
# ════════════════════════════════════════════════

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


def hotel_links(dest: str, dep: str, nights: int) -> tuple[str, str, int, int]:
    try:
        d  = datetime.fromisoformat(dep.replace("Z", "+00:00"))
        ci = d.strftime("%Y-%m-%d")
        co = (d + timedelta(days=nights)).strftime("%Y-%m-%d")
    except:
        n  = datetime.now()
        ci = n.strftime("%Y-%m-%d")
        co = (n + timedelta(days=nights)).strftime("%Y-%m-%d")

    city = city_name(dest)
    est_hostel = nights * 18
    est_hotel  = nights * 55

    bk = (f"https://www.booking.com/search.html"
          f"?ss={city}&checkin={ci}&checkout={co}"
          f"&group_adults=1&no_rooms=1&order=price")
    hw = (f"https://www.hostelworld.com/findabed.php"
          f"?ChosenCity={city}&DateFrom={ci}&DateTo={co}")

    return bk, hw, est_hostel, est_hotel


async def fmt_deal(deal: dict, one_way: bool, settings: dict) -> str:
    price    = deal["price"]
    avg      = avg_price(deal["origin"], deal["destination"], one_way)
    discount = round((avg - price) / avg * 100) if price < avg else 0
    stops    = "прямий ✈️" if deal["transfers"] == 0 else f"{deal['transfers']} пересадка"
    fire     = ("🔥🔥🔥" if discount >= 40 else
                "🔥🔥"  if discount >= 20 else
                "🔥"    if discount >  0  else "💰")

    orig = ap(deal["origin"])
    dest = ap(deal["destination"])

    msg  = f"{fire} *{orig}* → *{dest}*\n"
    msg += f"✈️ *€{price}*"
    if not one_way:
        msg += " туди-назад"
    msg += f"  |  {stops}"
    if deal["airline"]:
        msg += f"  |  {deal['airline']}"
    msg += "\n"

    if discount > 0:
        msg += f"📊 Середня ~€{avg}  →  дешевше на *{discount}%*\n"
    else:
        msg += f"📊 Середня ~€{avg}\n"

    dep_d = fmt_date(deal["departure_at"])
    msg  += f"📅 {dep_d}"
    if not one_way and deal.get("return_at"):
        ret_d  = fmt_date(deal["return_at"])
        n_str  = f" · {deal['nights']} н." if deal.get("nights") else ""
        msg   += f" — {ret_d}{n_str}"
    msg += "\n"

    # Готель
    if not one_way and settings["hotel"] and deal.get("nights") and deal.get("departure_at"):
        nights = deal["nights"]
        bk, hw, est_h, est_H = hotel_links(deal["destination"],
                                            deal["departure_at"], nights)
        budget = settings["budget"]
        tot_h  = price + est_h
        tot_H  = price + est_H
        ok_h   = "✅" if tot_h <= budget else "⚠️ дорого"
        ok_H   = "✅" if tot_H <= budget else "⚠️ дорого"

        msg += f"🏨 *{nights} ночей:*\n"
        msg += (f"  🛏 [Хостел ~€{est_h}]({hw}) → разом *€{tot_h}* {ok_h}\n"
                f"  🏩 [Готель ~€{est_H}]({bk}) → разом *€{tot_H}* {ok_H}\n")

    msg += f"🔗 [Дивитись на Aviasales]({deal['link']})\n\n"
    return msg


async def build_message(settings: dict) -> str:
    tasks, flags = [], []
    if settings["one_way"]:
        tasks.append(search_deals(True,  settings)); flags.append(True)
    if settings["ret"]:
        tasks.append(search_deals(False, settings)); flags.append(False)

    results = await asyncio.gather(*tasks)

    origin_label = (f"з {ap(settings['origin'])}"
                    if settings.get("origin") else f"{len(SEARCH_ORIGINS)} аеропортів")
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    h   = "✅" if settings["hotel"] else "❌"

    txt  = f"✈️ *FLIGHT DEALS* — {now}\n"
    txt += f"🔍 {origin_label} | 💶 €{settings['budget']} | {settings['region']} | 🏨{h}\n\n"

    for flag, deals in zip(flags, results):
        label  = "🛫 *В ОДИН БІК*" if flag else "🔄 *ТУДИ І НАЗАД* (до 7 н.)"
        h_note = " + 🏨" if (not flag and settings["hotel"]) else ""
        txt   += f"━━━━━━━━━━━━━━━━━━━━\n{label}{h_note}\n━━━━━━━━━━━━━━━━━━━━\n\n"

        if not deals:
            txt += "😔 Немає даних — API кеш порожній\n\n"
            continue

        count = 0
        for deal in deals:
            if count >= TOP_N:
                break
            txt += await fmt_deal(deal, flag, settings)
            count += 1

        # Зберігаємо для детекції нових deals
        k = "ow" if flag else "rt"
        prev_best.setdefault(settings.get("_cid", 0), {})[k] = deals[0]["price"]

    txt += "💡 _Ціни змінюються — бронюй швидко!_"
    return txt


# ════════════════════════════════════════════════
# FLIXBUS
# ════════════════════════════════════════════════

def flixbus_message() -> str:
    now  = datetime.now()
    nxt  = now.month % 12 + 1
    yr   = now.year + (1 if nxt == 1 else 0)
    date = f"01.{nxt:02d}.{yr}"
    mn   = ["","Січень","Лютий","Березень","Квітень","Травень","Червень",
            "Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"]

    routes = [
        ("Жешув","Варшава","1292","88"),     ("Краків","Варшава","28","88"),
        ("Краків","Відень","28","1"),         ("Краків","Берлін","28","2"),
        ("Краків","Прага","28","76"),         ("Варшава","Берлін","88","2"),
        ("Варшава","Прага","88","76"),        ("Варшава","Будапешт","88","26"),
        ("Варшава","Відень","88","1"),        ("Будапешт","Відень","26","1"),
        ("Будапешт","Загреб","26","162"),     ("Будапешт","Братислава","26","78"),
        ("Відень","Прага","1","76"),          ("Відень","Загреб","1","162"),
        ("Берлін","Амстердам","2","57"),      ("Берлін","Варшава","2","88"),
        ("Прага","Братислава","76","78"),     ("Бухарест","Клуж","395","393"),
        ("Бухарест","Яси","395","396"),       ("Кишинів","Бухарест","400","395"),
        ("Яси","Бухарест","396","395"),       ("Яси","Клуж","396","393"),
        ("Белград","Загреб","389","162"),     ("Белград","Будапешт","389","26"),
        ("Лісабон","Мадрид","45","17"),       ("Барселона","Мадрид","22","17"),
        ("Мілан","Рим","7","82"),             ("Мілан","Флоренція","7","96"),
        ("Париж","Ліон","13","30"),           ("Амстердам","Брюссель","57","25"),
    ]

    msg  = f"🚌 *FlixBus — {mn[nxt]} {yr}*\n\n"
    for fr, to, fi, ti in routes:
        url  = (f"https://shop.global.flixbus.com/s?"
                f"departureCity={fi}&arrivalCity={ti}"
                f"&rideDate={date}&adult=1&currency=EUR")
        msg += f"🚌 [{fr} → {to}]({url})\n"
    msg += f"\n🔍 [Всі маршрути FlixBus](https://www.flixbus.com/bus-routes)\n"
    msg += f"💡 _Натисни — перевіриш ціни на {mn[nxt]} {yr}_"
    return msg


# ════════════════════════════════════════════════
# КЛАВІАТУРИ
# ════════════════════════════════════════════════

def kb_main(cid: int) -> InlineKeyboardMarkup:
    s   = cfg(cid)
    h   = "🏨 ВКЛ ✅" if s["hotel"] else "🏨 ВИКЛ ❌"
    org = f"📍 {s['origin']}" if s.get("origin") else "📍 Всі аеропорти"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Шукати deals",        callback_data="search")],
        [InlineKeyboardButton(text="🚌 FlixBus наст. місяць", callback_data="flixbus")],
        [InlineKeyboardButton(text="💶 Бюджет",              callback_data="m_budget"),
         InlineKeyboardButton(text="🌍 Регіон",              callback_data="m_region")],
        [InlineKeyboardButton(text=h,                        callback_data="tog_hotel"),
         InlineKeyboardButton(text="🛫 Тип рейсу",          callback_data="m_type")],
        [InlineKeyboardButton(text=org,                      callback_data="m_origin")],
        [InlineKeyboardButton(text="⭐ Watchlist",            callback_data="m_watch")],
    ])


def kb_budget() -> InlineKeyboardMarkup:
    bs = [100, 150, 200, 300, 400, 500, 700, 1000]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"€{b}", callback_data=f"b_{b}") for b in bs[:4]],
        [InlineKeyboardButton(text=f"€{b}", callback_data=f"b_{b}") for b in bs[4:]],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


def kb_region() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=r, callback_data=f"reg_{i}")]
            for i, r in enumerate(REGIONS)]
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_type(cid: int) -> InlineKeyboardMarkup:
    s = cfg(cid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if s['one_way'] else '☐'} В один бік",
            callback_data="tog_ow")],
        [InlineKeyboardButton(
            text=f"{'✅' if s['ret'] else '☐'} Туди-назад",
            callback_data="tog_rt")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")],
    ])


def kb_origin_page(page: int = 0) -> InlineKeyboardMarkup:
    """Вибір аеропорту вильоту — по 8 на сторінку"""
    all_ap  = sorted(AIRPORTS.items(), key=lambda x: x[1])
    ps      = 8
    total   = len(all_ap)
    start   = page * ps
    end     = min(start + ps, total)
    rows    = []

    for code, name in all_ap[start:end]:
        rows.append([InlineKeyboardButton(
            text=f"{code} — {name.split(',')[0]}",
            callback_data=f"orig_{code}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"orig_p_{page-1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page+1}/{(total-1)//ps+1}", callback_data="noop"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"orig_p_{page+1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton(text="🌍 Всі аеропорти (скинути)", callback_data="orig_all")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_watch(cid: int) -> InlineKeyboardMarkup:
    ws   = watchlist.get(cid, [])
    rows = [[InlineKeyboardButton(
                text=f"🗑 {w['o']}→{w['d']} <€{w['p']}",
                callback_data=f"uw_{i}")]
            for i, w in enumerate(ws)]
    rows.append([InlineKeyboardButton(text="➕ Команда: /watch KRK LCA 60", callback_data="noop")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ════════════════════════════════════════════════
# ХЕНДЛЕРИ
# ════════════════════════════════════════════════

@dp.message(Command("start"))
async def on_start(m: Message):
    cfg(m.chat.id)
    await m.answer(
        "✈️ *Flight Deals Bot v8*\n\n"
        f"Пошук по *{len(SEARCH_ORIGINS)} аеропортах* Європи + Африка + Азія + Америка\n\n"
        "🛫 One-way і 🔄 Return до 7 ночей\n"
        "🏨 Готель в пакеті (Booking + Hostelworld)\n"
        "📍 Режим одного аеропорту (Яси→всюди→Яси)\n"
        "🚌 FlixBus наступний місяць\n"
        "⭐ Watchlist + авто-алерти\n"
        "🔔 Сповіщення нових deals кожні 6 год\n\n"
        "👇 Меню:",
        parse_mode="Markdown",
        reply_markup=kb_main(m.chat.id)
    )


@dp.message(Command("deals"))
async def on_deals(m: Message):
    s = cfg(m.chat.id)
    s["_cid"] = m.chat.id
    w = await m.answer("🔍 Шукаю deals... (~40 сек)")
    txt = await build_message(s)
    await w.delete()
    for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
        await m.answer(chunk, parse_mode="Markdown",
                       disable_web_page_preview=True,
                       reply_markup=kb_main(m.chat.id))


@dp.message(Command("flixbus"))
async def on_flixbus(m: Message):
    await m.answer(flixbus_message(), parse_mode="Markdown",
                   disable_web_page_preview=True)


@dp.message(Command("watch"))
async def on_watch(m: Message):
    p = m.text.split()
    if len(p) < 3:
        await m.answer(
            "⭐ *Watchlist*\n\nФормат: `/watch ЗВІДКИ КУДИ ЦІНА`\n"
            "Приклад: `/watch IAS LCA 70`\n"
            "Бот сповістить коли ціна впаде нижче вказаної!",
            parse_mode="Markdown")
        return
    o, d   = p[1].upper(), p[2].upper()
    thresh = int(p[3]) if len(p) > 3 and p[3].isdigit() else 80
    cid    = m.chat.id
    watchlist.setdefault(cid, [])
    for w in watchlist[cid]:
        if w["o"] == o and w["d"] == d:
            await m.answer("ℹ️ Вже є у watchlist!")
            return
    watchlist[cid].append({"o": o, "d": d, "p": thresh})
    await m.answer(
        f"⭐ Додано!\n*{ap(o)} → {ap(d)}*\n"
        f"Алерт коли ціна < *€{thresh}*",
        parse_mode="Markdown")


@dp.message(Command("airport"))
async def on_airport(m: Message):
    """Пошук аеропорту за назвою міста"""
    q = m.text.replace("/airport", "").strip().lower()
    if not q:
        await m.answer("Формат: `/airport Яси` або `/airport milan`",
                       parse_mode="Markdown")
        return
    found = [(k, v) for k, v in AIRPORTS.items()
             if q in v.lower() or q in k.lower()]
    if not found:
        await m.answer(f"Не знайдено: {q}")
        return
    txt = "🔍 *Знайдені аеропорти:*\n\n"
    for code, name in found[:10]:
        txt += f"• `{code}` — {name}\n"
    txt += "\nВикористай код для: `/watch IAS LCA 50`"
    await m.answer(txt, parse_mode="Markdown")


@dp.message(Command("help"))
async def on_help(m: Message):
    await m.answer(
        "📋 *Команди:*\n\n"
        "/start — головне меню\n"
        "/deals — пошук deals зараз\n"
        "/flixbus — автобуси наступний місяць\n"
        "/watch IAS LCA 70 — watchlist\n"
        "/airport Яси — знайти код аеропорту\n"
        "/help — довідка\n\n"
        "📍 *Режим одного аеропорту:*\n"
        "Меню → 📍 Всі аеропорти → вибери свій\n"
        "Бот шукатиме тільки звідти і туди\n\n"
        "🕘 Авто-deals щодня о 9:00\n"
        "🔔 Алерти нових deals кожні 6 год",
        parse_mode="Markdown")


# ── Callbacks ──

@dp.callback_query(F.data == "search")
async def cb_search(cb: CallbackQuery):
    await cb.answer()
    s = cfg(cb.message.chat.id)
    s["_cid"] = cb.message.chat.id
    w = await cb.message.answer("🔍 Шукаю deals... (~40 сек)")
    txt = await build_message(s)
    await w.delete()
    for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
        await cb.message.answer(chunk, parse_mode="Markdown",
                                disable_web_page_preview=True,
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "flixbus")
async def cb_flixbus(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer(flixbus_message(), parse_mode="Markdown",
                             disable_web_page_preview=True)


@dp.callback_query(F.data == "back")
async def cb_back(cb: CallbackQuery):
    await cb.answer()
    s = cfg(cb.message.chat.id)
    org = ap(s["origin"]) if s.get("origin") else "всі аеропорти"
    await cb.message.edit_text(
        f"⚙️ *Налаштування:*\n"
        f"💶 Бюджет: €{s['budget']} | Регіон: {s['region']}\n"
        f"🏨 Готель: {'✅' if s['hotel'] else '❌'} | "
        f"One-way: {'✅' if s['one_way'] else '❌'} | "
        f"Return: {'✅' if s['ret'] else '❌'}\n"
        f"📍 Аеропорт: {org}",
        parse_mode="Markdown",
        reply_markup=kb_main(cb.message.chat.id)
    )


@dp.callback_query(F.data == "m_budget")
async def cb_m_budget(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "💶 *Загальний бюджет* (квиток + готель):",
        parse_mode="Markdown", reply_markup=kb_budget())


@dp.callback_query(F.data.startswith("b_"))
async def cb_budget(cb: CallbackQuery):
    b = int(cb.data[2:])
    cfg(cb.message.chat.id)["budget"] = b
    await cb.answer(f"✅ Бюджет: €{b}")
    await cb.message.edit_text(f"✅ Бюджет встановлено: *€{b}*",
                                parse_mode="Markdown",
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "m_region")
async def cb_m_region(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🌍 *Регіон призначення:*",
                                parse_mode="Markdown", reply_markup=kb_region())


@dp.callback_query(F.data.startswith("reg_"))
async def cb_region(cb: CallbackQuery):
    idx    = int(cb.data[4:])
    region = list(REGIONS.keys())[idx]
    cfg(cb.message.chat.id)["region"] = region
    await cb.answer(f"✅ {region}")
    await cb.message.edit_text(f"✅ Регіон: *{region}*",
                                parse_mode="Markdown",
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "tog_hotel")
async def cb_tog_hotel(cb: CallbackQuery):
    s = cfg(cb.message.chat.id)
    s["hotel"] = not s["hotel"]
    status = "увімкнено ✅" if s["hotel"] else "вимкнено ❌"
    await cb.answer(f"🏨 {status}")
    try:
        await cb.message.edit_reply_markup(reply_markup=kb_main(cb.message.chat.id))
    except:
        await cb.message.answer(f"🏨 Готель {status}",
                                 reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "m_type")
async def cb_m_type(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("🛫 *Тип рейсу:*",
                                parse_mode="Markdown",
                                reply_markup=kb_type(cb.message.chat.id))


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


@dp.callback_query(F.data == "m_origin")
async def cb_m_origin(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text(
        "📍 *Вибери аеропорт вильоту:*\n"
        "_Бот шукатиме тільки з нього і назад в нього_",
        parse_mode="Markdown",
        reply_markup=kb_origin_page(0))


@dp.callback_query(F.data.startswith("orig_p_"))
async def cb_orig_page(cb: CallbackQuery):
    page = int(cb.data[7:])
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=kb_origin_page(page))


@dp.callback_query(F.data.startswith("orig_") & ~F.data.startswith("orig_p_") & ~F.data.startswith("orig_all"))
async def cb_orig_select(cb: CallbackQuery):
    code = cb.data[5:]
    s    = cfg(cb.message.chat.id)
    s["origin"] = code
    name = AIRPORTS.get(code, code)
    await cb.answer(f"✅ {code}")
    await cb.message.edit_text(
        f"📍 Вибрано: *{code}* — {name}\n\n"
        f"Тепер бот шукає тільки рейси *з {code}* і *назад в {code}*\n"
        f"_(наприклад: IAS → Мілан → Мадейра → Мілан → IAS)_",
        parse_mode="Markdown",
        reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "orig_all")
async def cb_orig_all(cb: CallbackQuery):
    cfg(cb.message.chat.id)["origin"] = None
    await cb.answer("✅ Всі аеропорти")
    await cb.message.edit_text("✅ Пошук по всіх аеропортах",
                                reply_markup=kb_main(cb.message.chat.id))


@dp.callback_query(F.data == "m_watch")
async def cb_m_watch(cb: CallbackQuery):
    await cb.answer()
    ws  = watchlist.get(cb.message.chat.id, [])
    txt = "⭐ *Watchlist*\n\n"
    txt += ("\n".join(f"• {ap(w['o'])} → {ap(w['d'])} — до *€{w['p']}*"
                      for w in ws)
            if ws else "_Порожньо._\nДодай: `/watch IAS LCA 60`")
    await cb.message.edit_text(txt, parse_mode="Markdown",
                                reply_markup=kb_watch(cb.message.chat.id))


@dp.callback_query(F.data.startswith("uw_"))
async def cb_uw(cb: CallbackQuery):
    i   = int(cb.data[3:])
    cid = cb.message.chat.id
    if cid in watchlist and i < len(watchlist[cid]):
        watchlist[cid].pop(i)
    await cb.answer("🗑 Видалено")
    await cb.message.edit_reply_markup(reply_markup=kb_watch(cid))


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery): await cb.answer()


# ════════════════════════════════════════════════
# ФОНОВІ ЗАДАЧІ
# ════════════════════════════════════════════════

async def task_daily():
    """Щоденна розсилка о 9:00"""
    for cid in list(user_cfg):
        try:
            s       = cfg(cid)
            s["_cid"] = cid
            txt     = await build_message(s)
            for chunk in [txt[i:i+4000] for i in range(0, len(txt), 4000)]:
                await bot.send_message(cid, chunk, parse_mode="Markdown",
                                       disable_web_page_preview=True,
                                       reply_markup=kb_main(cid))
        except Exception as e:
            log.error(f"daily {cid}: {e}")


async def task_watchlist():
    """Перевірка watchlist кожні 3 год"""
    for cid, watches in list(watchlist.items()):
        for w in watches:
            try:
                now = datetime.now()
                async with aiohttp.ClientSession() as session:
                    for i in range(1, 3):
                        month = (now + timedelta(days=30*i)).strftime("%Y-%m")
                        d = await api_get(session,
                            "https://api.travelpayouts.com/v1/prices/cheap",
                            {"origin": w["o"], "depart_date": month,
                             "currency": "eur", "one_way": "true", "market": "ua"})
                        if d and d.get("success") and d.get("data"):
                            dest_data = d["data"].get(w["d"], {})
                            for _, t in dest_data.items():
                                p = t.get("price", 0)
                                if 0 < p <= w["p"]:
                                    await bot.send_message(
                                        cid,
                                        f"🔔 *WATCHLIST АЛЕРТ!*\n\n"
                                        f"*{ap(w['o'])} → {ap(w['d'])}*\n"
                                        f"💶 *€{p}* — нижче порогу *€{w['p']}*!\n"
                                        f"🔗 [Дивитись]"
                                        f"(https://www.aviasales.com/search/{w['o']}{w['d']})",
                                        parse_mode="Markdown",
                                        disable_web_page_preview=True)
                                    break
            except Exception as e:
                log.error(f"watch {cid}: {e}")
            await asyncio.sleep(0.5)


async def task_new_deals():
    """Авто-сповіщення якщо з'явились нові deals (кожні 6 год)"""
    for cid in list(user_cfg):
        try:
            s       = cfg(cid)
            s["_cid"] = cid
            results = await asyncio.gather(
                search_deals(True,  s),
                search_deals(False, s),
            )
            flags   = ["ow", "rt"]
            new     = {}
            for flag, deals in zip(flags, results):
                if deals:
                    new[flag] = deals[0]["price"]

            prev  = prev_best.get(cid, {})
            alerts = []
            for flag, price in new.items():
                if flag in prev and price < prev[flag] * 0.85:
                    label = "one-way" if flag == "ow" else "туди-назад"
                    drop  = round((1 - price/prev[flag]) * 100)
                    alerts.append(
                        f"📉 *{label}*: €{price:.0f} "
                        f"(було €{prev[flag]:.0f}, -{drop}%)"
                    )
            prev_best[cid] = new

            if alerts:
                await bot.send_message(
                    cid,
                    "🔔 *НОВІ DEALS!*\n\n" + "\n".join(alerts) +
                    "\n\nНатисни /deals щоб переглянути!",
                    parse_mode="Markdown",
                    reply_markup=kb_main(cid))
        except Exception as e:
            log.error(f"new_deals {cid}: {e}")


# ════════════════════════════════════════════════
# ЗАПУСК
# ════════════════════════════════════════════════

async def main():
    await bot.set_my_commands([
        BotCommand(command="start",   description="Головне меню"),
        BotCommand(command="deals",   description="Пошук deals зараз"),
        BotCommand(command="flixbus", description="FlixBus наступний місяць"),
        BotCommand(command="watch",   description="/watch IAS LCA 70 — відстежувати"),
        BotCommand(command="airport", description="/airport Яси — знайти код"),
        BotCommand(command="help",    description="Довідка"),
    ])

    scheduler.add_job(task_daily,      "cron", hour=9,      minute=0)
    scheduler.add_job(task_watchlist,  "cron", hour="*/3",  minute=30)
    scheduler.add_job(task_new_deals,  "cron", hour="*/6",  minute=15)
    scheduler.start()

    log.info(f"Bot v8 started | {len(AIRPORTS)} airports | {len(SEARCH_ORIGINS)} origins")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
