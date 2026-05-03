"""
CyberWatch UZ Bot — Asosiy modul (Entry Point).

Scheduler bilan barcha kanallarni kuzatadi,
yangi postlarni tarjima qilib Telegram kanalga yuboradi.
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import Config, SourceChannel, config, setup_logging
from src.deduplicator import Deduplicator
from src.fetcher import TweetFetcher
from src.filter import is_cyber_related
from src.telegram_poster import TelegramPoster
from src.translator import Translator

logger = logging.getLogger(__name__)

# Graceful shutdown uchun event
shutdown_event = asyncio.Event()


async def process_channel(
    channel_cfg: SourceChannel,
    fetcher: TweetFetcher,
    dedup: Deduplicator,
    translator: Translator,
    poster: TelegramPoster,
    max_posts: int,
    post_interval: int,
) -> int:
    """
    Bitta kanalni qayta ishlaydi: fetch → filter → dedup → translate → post.

    Args:
        channel_cfg: Kanal konfiguratsiyasi.
        fetcher: Tweet fetcher.
        dedup: Deduplicator.
        translator: Tarjimon.
        poster: Telegram poster.
        max_posts: Siklda maksimal post soni.
        post_interval: Postlar orasidagi interval (sekundlarda).

    Returns:
        Yuborilgan postlar soni.
    """
    username = channel_cfg.username
    logger.info("Kanal qayta ishlanmoqda: @%s", username)

    try:
        tweets = await fetcher.fetch_tweets(username)
    except Exception as e:
        logger.error("Fetcher xatosi @%s: %s", username, str(e))
        return 0

    if not tweets:
        logger.info("@%s: yangi tweet topilmadi", username)
        return 0

    posted_count = 0

    for tweet in tweets:
        if posted_count >= max_posts:
            logger.info(
                "@%s: maksimal post soni (%d) ga yetildi, to'xtatilmoqda",
                username, max_posts,
            )
            break

        # Shutdown tekshiruvi
        if shutdown_event.is_set():
            logger.info("Shutdown signali aniqlandi, sikl to'xtatilmoqda")
            break

        # Keyword filter (faqat DeepTechTR uchun)
        if channel_cfg.filter_enabled and not is_cyber_related(tweet.original_text):
            logger.debug(
                "@%s: post filtrlandi (cyber emas): %s...",
                username, tweet.original_text[:50],
            )
            continue

        # Deduplication tekshiruvi
        try:
            is_dup = await dedup.is_duplicate(
                tweet_id=tweet.tweet_id,
                source=tweet.username,
                text=tweet.original_text,
            )
            if is_dup:
                logger.debug("@%s: duplikat — %s", username, tweet.tweet_id)
                continue
        except Exception as e:
            logger.error("Dedup xatosi: %s", str(e))
            continue

        # Tarjima
        try:
            translated = await translator.translate(tweet.original_text)
        except Exception as e:
            logger.error("Tarjima xatosi: %s", str(e))
            translated = tweet.original_text

        # Telegram ga yuborish
        published_str = tweet.published_at.strftime("%Y-%m-%d %H:%M UTC")

        success = await poster.send_post(
            emoji=channel_cfg.emoji,
            source_name=channel_cfg.display_name,
            translated_text=translated,
            tweet_url=tweet.tweet_url,
            published_at=published_str,
            image_url=tweet.image_url,
            media_type=tweet.media_type,
        )

        if success:
            # Dedup bazaga yozish
            try:
                await dedup.mark_posted(
                    tweet_id=tweet.tweet_id,
                    source=tweet.username,
                    text=tweet.original_text,
                )
            except Exception as e:
                logger.error("Dedup belgilash xatosi: %s", str(e))

            posted_count += 1
            logger.info(
                "@%s: post yuborildi (%d/%d) — %s",
                username, posted_count, max_posts, tweet.tweet_url,
            )

            # Postlar orasida kutish (spam oldini olish)
            if posted_count < max_posts:
                await asyncio.sleep(post_interval)

    return posted_count


async def poll_all_channels(
    cfg: Config,
    fetcher: TweetFetcher,
    dedup: Deduplicator,
    translator: Translator,
    poster: TelegramPoster,
) -> None:
    """Barcha kanallarni kuzatadi (bitta poll sikli)."""
    logger.info("═══ Poll sikli boshlandi ═══")
    total_posted = 0

    for channel in cfg.source_channels:
        if shutdown_event.is_set():
            break

        count = await process_channel(
            channel_cfg=channel,
            fetcher=fetcher,
            dedup=dedup,
            translator=translator,
            poster=poster,
            max_posts=cfg.max_posts_per_cycle,
            post_interval=cfg.post_interval_seconds,
        )
        total_posted += count

        # Kanallar orasida 5 soniya kutish (rate limit uchun)
        if not shutdown_event.is_set():
            await asyncio.sleep(5)

    logger.info("═══ Poll sikli tugadi: jami %d ta post yuborildi ═══", total_posted)


async def cleanup_database(dedup: Deduplicator) -> None:
    """Eski DB yozuvlarini tozalaydi (haftalik/kunlik task)."""
    logger.info("DB tozalash boshlandi...")
    try:
        deleted = await dedup.cleanup_old_records(days=30)
        logger.info("DB tozalash tugadi: %d ta yozuv o'chirildi", deleted)
    except Exception as e:
        logger.error("DB tozalash xatosi: %s", str(e))


def handle_shutdown(sig: signal.Signals) -> None:
    """Graceful shutdown signal handler."""
    logger.info("Signal qabul qilindi: %s — bot to'xtatilmoqda...", sig.name)
    shutdown_event.set()


async def main() -> None:
    """Bot ning asosiy funksiyasi."""
    # 1. Logging sozlash
    setup_logging(config)
    logger.info("CyberWatch UZ Bot ishga tushmoqda...")

    # 2. Konfiguratsiyani tekshirish
    try:
        config.validate()
        logger.info("Konfiguratsiya tekshirildi ✓")
    except ValueError as e:
        logger.critical("Konfiguratsiya xatosi:\n%s", str(e))
        sys.exit(1)

    # 3. DB papkasini yaratish
    db_dir = Path(config.db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # 4. Komponentlarni ishga tushirish
    dedup = Deduplicator(config.db_path)
    await dedup.init_db()

    fetcher = TweetFetcher()
    await fetcher.start()

    translator = Translator(config.gemini_api_key)
    translator.setup()

    poster = TelegramPoster(config.telegram_bot_token, config.telegram_channel_id)

    # 5. Signal handler (graceful shutdown)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_shutdown, sig)
        except NotImplementedError:
            # Windows da signal_handler ishlamasligi mumkin
            signal.signal(sig, lambda s, f: handle_shutdown(signal.Signals(s)))

    # 6. Startup xabari
    await poster.send_startup_message()

    # 7. Scheduler sozlash
    scheduler = AsyncIOScheduler()

    # Har N daqiqada poll qilish
    scheduler.add_job(
        poll_all_channels,
        trigger="interval",
        minutes=config.poll_interval_minutes,
        args=[config, fetcher, dedup, translator, poster],
        id="poll_channels",
        name="Kanallarni kuzatish",
        next_run_time=datetime.now(timezone.utc),  # Darhol birinchi marta ishlatish
    )

    # Har kuni 00:00 da DB tozalash
    scheduler.add_job(
        cleanup_database,
        trigger="cron",
        hour=0,
        minute=0,
        args=[dedup],
        id="cleanup_db",
        name="DB tozalash",
    )

    scheduler.start()
    logger.info(
        "Scheduler ishga tushdi: har %d daqiqada poll, har kuni 00:00 da tozalash",
        config.poll_interval_minutes,
    )

    # 8. Shutdown kutish
    try:
        await shutdown_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatilmoqda (keyboard interrupt)...")

    # 9. Graceful shutdown
    logger.info("Resurslar yopilmoqda...")
    scheduler.shutdown(wait=False)
    await fetcher.close()
    await dedup.close()
    logger.info("CyberWatch UZ Bot to'xtatildi. Xayr! 👋")


if __name__ == "__main__":
    asyncio.run(main())
