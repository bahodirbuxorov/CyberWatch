# 🛡️ CyberWatch UZ Bot

X (Twitter) dagi kiberxavfsizlik kanallarini kuzatib, yangi postlarni avtomatik **O'zbek tiliga** tarjima qilib, Telegram kanalga yuboruvchi bot.

---

## 📋 Imkoniyatlar

- **4 ta X kanalni** real vaqtda kuzatish (Nitter RSS orqali)
- **Google Gemini AI** yordamida professional tarjima
- **Ikki darajali deduplication** — bir xil postni takrorlamaslik
- **Keyword filter** — DeepTechTR dan faqat kiberxavfsizlik mavzularini o'tkazish
- **Docker** bilan qulay deploy
- **Self-hosted Nitter** — Twitter API kerak emas

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

### 3-qadam: Konfiguratsiya

```bash
cp .env.example .env
```

`.env` faylini tahrirlang:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=@cyberwatch_uz
GEMINI_API_KEY=AIzaSy...your_key_here
POLL_INTERVAL_MINUTES=15
MAX_POSTS_PER_CYCLE=5
DB_PATH=/app/data/bot.db
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
│   ├── fetcher.py           # Nitter RSS dan tweet olish
│   ├── translator.py        # Gemini orqali tarjima
│   ├── telegram_poster.py   # Telegram kanalga post qilish
│   ├── deduplicator.py      # SQLite dedup logic
│   └── filter.py            # DeepTechTR uchun keyword filter
├── data/
│   └── .gitkeep             # SQLite DB shu yerda saqlanadi
├── logs/
│   └── .gitkeep
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Nitter haqida

[Nitter](https://github.com/zedeus/nitter) — bu X (Twitter) ning ochiq kodli frontend alternative. Bot Nitter RSS orqali tweetlarni oladi, shuning uchun **Twitter API kerak emas**.

### Nitter ishlash tartibi:
1. Docker Compose da `nitter` servisi avtomatik ishga tushadi
2. Bot birinchi navbatda self-hosted Nitter ga murojaat qiladi
3. Agar self-hosted ishlamasa, public instance'larga o'tadi (fallback)

### Public Nitter instance'lar:
- `https://nitter.privacydev.net`
- `https://nitter.poast.org`
- `https://nitter.1d4.us`
- `https://nitter.adminforge.de`

> ⚠️ **Eslatma:** Public Nitter instance'lar vaqti-vaqti bilan ishlamay qolishi mumkin. Self-hosted Nitter tavsiya etiladi.

---

## 🔧 Muammolarni bartaraf etish (Troubleshooting)

### Bot ishga tushmayapti

**Xato:** `Konfiguratsiya xatolari: TELEGRAM_BOT_TOKEN bo'sh`
- `.env` faylida barcha kalitlar to'g'ri yozilganini tekshiring
- `.env` faylida bo'sh joylar yoki tirnoq belgilari yo'qligiga ishonch hosil qiling

### Telegram ga xabar yuborilmayapti

- Bot kanalga **admin** sifatida qo'shilganini tekshiring
- Channel ID to'g'ri formatda ekanligini tekshiring (`@channel_name` yoki `-100...`)
- BotFather dan bot **aktiv** ekanligini tasdiqlang

### Nitter dan ma'lumot kelmayapti

- `docker-compose logs nitter` bilan Nitter holatini tekshiring
- Public instance'lar vaqtincha ishlamay qolgan bo'lishi mumkin
- Nitter konteynerini qayta ishga tushiring: `docker-compose restart nitter`

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
| Nitter RSS | X dan ma'lumot olish |
| feedparser | RSS parse |
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
