# ✈️ Flight Deals Bot — Інструкція запуску

## Що це
Telegram бот який щодня шукає найдешевші квитки з України
куди завгодно по світу і надсилає їх тобі в Telegram.

---

## Крок 1 — Вписати свої ключі у bot.py

Відкрий файл `bot.py` і знайди рядки вгорі:

```python
TELEGRAM_TOKEN = "ВАШ_TELEGRAM_TOKEN_ТУТ"
TRAVELPAYOUTS_TOKEN = "ВАШ_TRAVELPAYOUTS_TOKEN_ТУТ"
```

Заміни на свої реальні ключі:
- `TELEGRAM_TOKEN` — токен від @BotFather в Telegram
- `TRAVELPAYOUTS_TOKEN` — токен з travelpayouts.com → Tools → API

---

## Крок 2 — Завантажити на GitHub

1. Зайди на https://github.com і зареєструйся (безкоштовно)
2. Натисни "New repository" → назви `flight-bot` → Create
3. Завантаж всі 3 файли: `bot.py`, `requirements.txt`, `railway.toml`
   - Натисни "uploading an existing file" → перетягни файли → Commit

---

## Крок 3 — Запустити на Railway (безкоштовно)

1. Зайди на https://railway.app
2. "Login with GitHub" — авторизуйся через GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Вибери свій репозиторій `flight-bot`
5. Railway автоматично запустить бота!

---

## Крок 4 — Перевірити що працює

1. Знайди свого бота в Telegram (за username який ти задав)
2. Натисни /start
3. Бот повинен одразу показати deals!

---

## Налаштування (в bot.py)

```python
ORIGIN_CITIES = ["KBP", "LWO", "IEV"]  # міста вильоту
MAX_PRICE_EUR = 100                      # максимальна ціна
TOP_DEALS_COUNT = 5                      # скільки deals показувати
```

Популярні IATA коди:
- KBP — Київ Бориспіль
- IEV — Київ Жуляни  
- LWO — Львів
- CWC — Чернівці
- ODS — Одеса
- HRK — Харків

---

## Команди бота

- `/start` — підписатись на щоденні deals
- `/deals` — показати deals прямо зараз
- `/help` — допомога

Бот надсилає deals автоматично щодня о 9:00 ранку.
