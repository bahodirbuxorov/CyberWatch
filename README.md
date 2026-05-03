# 🛡️ CyberWatch UZ Bot

X (Twitter) dagi kiberxavfsizlik kanallarini kuzatib, yangi postlarni avtomatik **O'zbek tiliga** tarjima qilib, Telegram kanalga yuboruvchi bot.

---

## 📋 Imkoniyatlar

- **4 ta X kanalni** real vaqtda kuzatish (twikit orqali)
- **Google Gemini AI** yordamida professional tarjima
- **Ikki darajali deduplication** — bir xil postni takrorlamaslik
- **Keyword filter** — DeepTechTR dan faqat kiberxavfsizlik mavzularini o'tkazish
- **Docker** bilan qulay deploy
- **Twitter API kerak emas** — twikit X ning ichki API si orqali ishlaydi

## 📡 Kuzatiladigan kanallar

| Kanal | Turi | Filter |
|-------|------|--------|
| [@VECERTRadar](https://x.com/VECERTRadar) | 🛡️ Barcha postlar | Yo'q |
| [@DarkWebInformer](https://x.com/DarkWebInformer) | 🕵️ Barcha postlar | Yo'q |
| [@DailyDarkWeb](https://x.com/DailyDarkWeb) | 🌑 Barcha postlar | Yo'q |
| [@DeepTechTR](https://x.com/DeepTechTR) | ⚡ Cybersecurity only | ✅ Ha |

---

## 🚀 O'rnatish va ishga tushirish

### 1-qadam: Repozitoriyani klonlash

```bash
git clone https://github.com/your-username/cyberwatch-uz-bot.git
cd cyberwatch-uz-bot
```

### 2-qadam: API kalitlarini olish

#### Telegram Bot Token
1. Telegram da [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `CyberWatch UZ Bot`)
4. Bot username kiriting (masalan: `cyberwatch_uz_bot`)
5. BotFather sizga **token** beradi — uni saqlang

#### Telegram Channel ID
1. Telegram da kanal yarating yoki mavjudini ishlating
2. Botni kanalga **admin** sifatida qo'shing
3. Channel ID: `@kanal_username` yoki `-100XXXXXXXXXX` formatida

#### Google Gemini API Key
1. [Google AI Studio](https://aistudio.google.com/apikey) ga kiring
2. **"Create API Key"** tugmasini bosing
3. API kalitni nusxalang

#### X (Twitter) Account
Bot X dan ma'lumot olish uchun bitta X account kerak (Twitter API emas!). 
**Twikit** kutubxonasi X ning ichki web API si orqali ishlaydi.

1. X da yangi yoki kam ishlatilgan account yarating
2. Account ga email va parol o'rnating
3. `.env` faylga username, email va parolni yozing

> ⚠️ **Muhim:** Asosiy shaxsiy accountingizni ishlatmang! 
> Alohida bot account yarating. Account bloklash xavfi bor.

### 3-qadam: Konfiguratsiya

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=@cyberwatch_uz
GEMINI_API_KEY=AIzaSy...your_key_here

# X account (yangi/alohida account tavsiya etiladi)
X_USERNAME=your_x_username
X_EMAIL=your_x_email@example.com
X_PASSWORD=your_x_password

POLL_INTERVAL_MINUTES=15
MAX_POSTS_PER_CYCLE=5
DB_PATH=/app/data/bot.db
COOKIES_PATH=/app/data/cookies.json
LOG_LEVEL=INFO
LOG_FILE=/app/logs/bot.log
```

### 4-qadam: Docker bilan ishga tushirish

```bash
docker-compose up -d --build
```

Bot ishga tushadi va Telegram kanalga quyidagi xabarni yuboradi:
> ✅ CyberWatch UZ Bot ishga tushdi

### Loglarni ko'rish

```bash
# Docker loglar
docker-compose logs -f bot

# Fayl loglar
tail -f logs/bot.log
```

### Bot ni to'xtatish

```bash
docker-compose down
```

---

## 🛠️ Docker siz ishga tushirish (development)

```bash
# Virtual muhit yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows

# Dependencies o'rnatish
pip install -r requirements.txt

# .env faylini sozlash
cp .env.example .env
# .env ni tahrirlang

# DB va log papkalarini yaratish
mkdir -p data logs

# Botni ishga tushirish
python -m src.main
```

---

## 📁 Fayl strukturasi

```
cyberwatch-uz-bot/
├── src/
│   ├── __init__.py          # Package init
│   ├── main.py              # Entry point, scheduler
│   ├── config.py            # Barcha sozlamalar
│   ├── fetcher.py           # Twikit orqali tweet olish
│   ├── translator.py        # Gemini orqali tarjima
│   ├── telegram_poster.py   # Telegram kanalga post qilish
│   ├── deduplicator.py      # SQLite dedup logic
│   └── filter.py            # DeepTechTR uchun keyword filter
├── data/
│   └── .gitkeep             # SQLite DB va cookies shu yerda
├── logs/
│   └── .gitkeep
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Twikit haqida

[Twikit](https://github.com/d60/twikit) — bu X (Twitter) ning ichki web API si orqali 
ishlaydigan Python kutubxonasi. Rasmiy Twitter API kerak emas.

### Qanday ishlaydi:
1. Bot birinchi marta ishga tushganda X ga login qiladi
2. Cookies faylga saqlanadi (`data/cookies.json`)
3. Keyingi ishga tushirishlarda cookies dan foydalanadi (qayta login kerak emas)
4. Agar cookies muddati tugasa, avtomatik qayta login qiladi

### Muhim eslatmalar:
- **Alohida X account** yarating — asosiy accountingizni ishlatmang
- Bot X ning rate limit laridan himoyalangan (kanallar orasida 5s kutish)
- Agar account bloklansa, yangi account bilan `.env` ni yangilang

---

## 🔧 Muammolarni bartaraf etish (Troubleshooting)

### Bot ishga tushmayapti

**Xato:** `Konfiguratsiya xatolari: TELEGRAM_BOT_TOKEN bo'sh`
- `.env` faylida barcha kalitlar to'g'ri yozilganini tekshiring
- `.env` faylida bo'sh joylar yoki tirnoq belgilari yo'qligiga ishonch hosil qiling

### X ga login qilib bo'lmayapti

- X_USERNAME, X_EMAIL va X_PASSWORD to'g'ri ekanligini tekshiring
- X account ga 2FA (ikki faktorli autentifikatsiya) O'CHIRILGAN bo'lishi kerak
- Agar "Could not authenticate" xatosi bo'lsa:
  1. `data/cookies.json` faylini o'chiring
  2. Bot ni qayta ishga tushiring
- Account bloklanmagan bo'lishi kerak — X da tekshiring

### Telegram ga xabar yuborilmayapti

- Bot kanalga **admin** sifatida qo'shilganini tekshiring
- Channel ID to'g'ri formatda ekanligini tekshiring (`@channel_name` yoki `-100...`)
- BotFather dan bot **aktiv** ekanligini tasdiqlang

### Tarjima ishlamayapti

- Gemini API kaliti to'g'ri va faol ekanligini [Google AI Studio](https://aistudio.google.com/) da tekshiring
- Bepul tier limitiga yetgan bo'lishingiz mumkin (kuniga 60 ta so'rov)
- Tarjima xatosi bo'lsa, bot original inglizcha matnni yuboradi

### DB bilan muammo

- `data/` papkasiga yozish ruxsati borligini tekshiring
- DB ni tozalash: `rm data/bot.db` va botni qayta ishga tushiring

### Loglarni tekshirish

```bash
# Oxirgi 100 qator log
tail -100 logs/bot.log

# Real vaqtda kuzatish
tail -f logs/bot.log

# Xatolarni qidirish
grep "ERROR" logs/bot.log
```

---

## 📊 Texnologiyalar

| Texnologiya | Maqsad |
|-------------|--------|
| Python 3.11 | Asosiy til |
| twikit | X dan ma'lumot olish (ichki API) |
| Google Gemini 1.5 Flash | AI tarjima |
| python-telegram-bot v21+ | Telegram API |
| aiosqlite | Deduplication DB |
| APScheduler | Vazifalar jadvali |
| Docker + Compose | Deploy |

---

## 📜 Litsenziya

MIT License

---

> 🇺🇿 **CyberWatch UZ** — O'zbekiston uchun kiberxavfsizlik yangiliklari, avtomatik tarjimada.
