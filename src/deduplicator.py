"""
CyberWatch UZ Bot — Deduplication moduli.

SQLite yordamida ikki darajali dedup:
  1-daraja: tweet_id + source (exact match)
  2-daraja: content_hash (SHA-256) — turli manbalardan bir xil xabar
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone

import aiosqlite

logger = logging.getLogger(__name__)

# SQL sxemasi
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS posted_tweets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id     TEXT    NOT NULL,
    source       TEXT    NOT NULL,
    content_hash TEXT    NOT NULL,
    posted_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(tweet_id, source)
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_content_hash ON posted_tweets(content_hash);
"""


def _normalize_text(text: str) -> str:
    """Matnni normalizatsiya qiladi (hash uchun)."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"https?://\S+", "", text)  # URL larni olib tashlash
    return text.strip()


def compute_content_hash(text: str) -> str:
    """Matn uchun SHA-256 hash hisoblaydi (normalized)."""
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class Deduplicator:
    """Asinxron SQLite dedup menejeri."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """Bazani ochadi va jadval tuzadi."""
        logger.info("SQLite bazasi ochilmoqda: %s", self.db_path)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute(_CREATE_TABLE_SQL)
        await self._db.execute(_CREATE_INDEX_SQL)
        await self._db.commit()
        logger.info("SQLite bazasi tayyor")

    async def close(self) -> None:
        """Bazani yopadi."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("SQLite bazasi yopildi")

    async def is_duplicate(self, tweet_id: str, source: str, text: str) -> bool:
        """
        Ikki darajali dedup tekshiruvi.

        Args:
            tweet_id: Tweet identifikatori.
            source: Manba kanal username.
            text: Tweet matni.

        Returns:
            True agar bu tweet allaqachon yuborilgan bo'lsa.
        """
        if not self._db:
            raise RuntimeError("Baza ochilmagan. init_db() ni chaqiring.")

        # 1-daraja: tweet_id + source
        cursor = await self._db.execute(
            "SELECT 1 FROM posted_tweets WHERE tweet_id = ? AND source = ?",
            (tweet_id, source),
        )
        row = await cursor.fetchone()
        if row:
            logger.debug("Dedup 1-daraja: tweet_id=%s source=%s — duplikat", tweet_id, source)
            return True

        # 2-daraja: content_hash
        content_hash = compute_content_hash(text)
        cursor = await self._db.execute(
            "SELECT 1 FROM posted_tweets WHERE content_hash = ?",
            (content_hash,),
        )
        row = await cursor.fetchone()
        if row:
            logger.debug("Dedup 2-daraja: hash=%s — duplikat (boshqa manba)", content_hash[:16])
            return True

        return False

    async def mark_posted(self, tweet_id: str, source: str, text: str) -> None:
        """Tweetni yuborilgan deb belgilaydi."""
        if not self._db:
            raise RuntimeError("Baza ochilmagan. init_db() ni chaqiring.")

        content_hash = compute_content_hash(text)
        now = datetime.now(timezone.utc).isoformat()

        try:
            await self._db.execute(
                "INSERT INTO posted_tweets (tweet_id, source, content_hash, posted_at) "
                "VALUES (?, ?, ?, ?)",
                (tweet_id, source, content_hash, now),
            )
            await self._db.commit()
            logger.debug("Dedup: tweet_id=%s source=%s belgilandi", tweet_id, source)
        except aiosqlite.IntegrityError:
            logger.warning("Dedup: tweet_id=%s source=%s allaqachon mavjud", tweet_id, source)

    async def cleanup_old_records(self, days: int = 30) -> int:
        """Eski yozuvlarni o'chiradi.

        Args:
            days: Necha kundan eski yozuvlarni o'chirish.

        Returns:
            O'chirilgan yozuvlar soni.
        """
        if not self._db:
            raise RuntimeError("Baza ochilmagan. init_db() ni chaqiring.")

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = await self._db.execute(
            "DELETE FROM posted_tweets WHERE posted_at < ?",
            (cutoff,),
        )
        await self._db.commit()
        deleted = cursor.rowcount
        logger.info("Dedup tozalash: %d ta eski yozuv o'chirildi (%d kundan eski)", deleted, days)
        return deleted
