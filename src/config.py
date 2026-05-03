"""
CyberWatch UZ Bot — Konfiguratsiya moduli.

Barcha sozlamalar .env faylidan o'qiladi.
Default qiymatlar mavjud.
"""

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, field
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()


@dataclass
class NitterInstance:
    """Bitta Nitter instance ma'lumotlari."""
    url: str
    priority: int = 0


@dataclass
class SourceChannel:
    """Kuzatiladigan X (Twitter) kanali."""
    username: str
    display_name: str
    emoji: str
    filter_enabled: bool = False


@dataclass
class Config:
    """Bot uchun barcha sozlamalar."""

    # — Telegram —
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_channel_id: str = os.getenv("TELEGRAM_CHANNEL_ID", "")

    # — Gemini AI —
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    # — Scheduler —
    poll_interval_minutes: int = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
    max_posts_per_cycle: int = int(os.getenv("MAX_POSTS_PER_CYCLE", "5"))
    post_interval_seconds: int = int(os.getenv("POST_INTERVAL_SECONDS", "30"))

    # — Database —
    db_path: str = os.getenv("DB_PATH", "data/bot.db")

    # — Logging —
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/bot.log")

    # — Nitter instances (fallback chain) —
    nitter_instances: list[NitterInstance] = field(default_factory=lambda: [
        NitterInstance(url="https://nitter.privacydev.net", priority=1),
        NitterInstance(url="https://nitter.poast.org", priority=2),
        NitterInstance(url="https://nitter.1d4.us", priority=3),
        NitterInstance(url="https://nitter.adminforge.de", priority=4),
    ])

    def __post_init__(self) -> None:
        """Self-hosted Nitter instance ni qo'shadi (agar mavjud bo'lsa)."""
        self_hosted = os.getenv("NITTER_SELF_HOSTED_URL", "")
        if self_hosted:
            self.nitter_instances.insert(
                0, NitterInstance(url=self_hosted.rstrip("/"), priority=0)
            )

    # — Kuzatiladigan kanallar —
    source_channels: list[SourceChannel] = field(default_factory=lambda: [
        SourceChannel(
            username="VECERTRadar",
            display_name="VE-CERT Radar",
            emoji="🛡️",
            filter_enabled=False,
        ),
        SourceChannel(
            username="DarkWebInformer",
            display_name="Dark Web Informer",
            emoji="🕵️",
            filter_enabled=False,
        ),
        SourceChannel(
            username="DailyDarkWeb",
            display_name="Daily Dark Web",
            emoji="🌑",
            filter_enabled=False,
        ),
        SourceChannel(
            username="DeepTechTR",
            display_name="DeepTech TR",
            emoji="⚡",
            filter_enabled=True,
        ),
    ])

    def validate(self) -> None:
        """Barcha muhim sozlamalarni tekshiradi. Bo'sh bo'lsa xato beradi."""
        errors: list[str] = []
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN bo'sh yoki mavjud emas")
        if not self.telegram_channel_id:
            errors.append("TELEGRAM_CHANNEL_ID bo'sh yoki mavjud emas")
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY bo'sh yoki mavjud emas")
        if errors:
            raise ValueError(
                "Konfiguratsiya xatolari:\n" + "\n".join(f"  - {e}" for e in errors)
            )


def setup_logging(config: Config) -> None:
    """Logging tizimini sozlaydi (console + rotating file)."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Log papkasini yaratish
    log_dir = Path(config.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (rotating: 5 MB, 5 backups)
    file_handler = RotatingFileHandler(
        filename=config.log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.info("Logging tizimi sozlandi (level=%s)", config.log_level)


# Global config instance
config = Config()
