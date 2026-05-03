"""
CyberWatch UZ Bot — RSS Fetcher moduli.

Nitter RSS orqali X (Twitter) postlarini oladi.
Fallback chain bilan bir nechta Nitter instance'larni sinaydi.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime

import aiohttp
import feedparser

from src.config import Config, NitterInstance

logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    """Bitta tweet ma'lumotlari."""
    tweet_id: str
    username: str
    original_text: str
    tweet_url: str
    published_at: datetime


class RSSFetcher:
    """Nitter RSS dan tweetlarni oluvchi klass."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.instances = sorted(
            config.nitter_instances,
            key=lambda inst: inst.priority,
        )
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """HTTP sessiyani ochadi."""
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)
        logger.info("RSS Fetcher HTTP sessiyasi ochildi")

    async def close(self) -> None:
        """HTTP sessiyani yopadi."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("RSS Fetcher HTTP sessiyasi yopildi")

    async def _fetch_rss(self, instance: NitterInstance, username: str) -> str | None:
        """
        Bitta Nitter instance'dan RSS olishga harakat qiladi.

        Args:
            instance: Nitter instance.
            username: X username (@ siz).

        Returns:
            RSS XML matni yoki None (xato bo'lsa).
        """
        url = f"{instance.url}/{username}/rss"
        try:
            if not self._session:
                raise RuntimeError("HTTP sessiya ochilmagan. start() ni chaqiring.")

            logger.debug("RSS so'rov: %s", url)
            async with self._session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    logger.debug("RSS muvaffaqiyatli olindi: %s (%d belgi)", url, len(text))
                    return text
                else:
                    logger.warning(
                        "RSS xato: %s → HTTP %d",
                        url, response.status,
                    )
                    return None
        except aiohttp.ClientError as e:
            logger.warning("RSS ulanish xatosi: %s → %s", url, str(e))
            return None
        except Exception as e:
            logger.error("RSS kutilmagan xato: %s → %s", url, str(e))
            return None

    def _is_retweet_or_reply(self, text: str) -> bool:
        """Retweet yoki Reply ekanligini tekshiradi."""
        stripped = text.strip()
        if stripped.startswith("RT @"):
            return True
        if stripped.startswith("@"):
            return True
        return False

    def _parse_entry(self, entry: feedparser.FeedParserDict, username: str) -> Tweet | None:
        """
        Bitta RSS entry ni Tweet ga o'giradi.

        Args:
            entry: feedparser entry.
            username: Manba kanal username.

        Returns:
            Tweet obyekti yoki None (filter qilinsa).
        """
        # Matnni olish
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        text = title if title else summary

        # HTML taglarini olib tashlash (sodda usul)
        import re
        text = re.sub(r"<[^>]+>", "", text).strip()

        if not text:
            return None

        # RT va Reply filtrlash
        if self._is_retweet_or_reply(text):
            logger.debug("Fetcher: RT/Reply filtrlandi — %s", text[:50])
            return None

        # Tweet ID
        tweet_id = entry.get("id", entry.get("link", ""))

        # Tweet URL
        tweet_url = entry.get("link", "")

        # Vaqt
        published = entry.get("published_parsed")
        if published:
            published_at = datetime.fromtimestamp(
                mktime(published),
                tz=timezone.utc,
            )
        else:
            published_at = datetime.now(timezone.utc)

        return Tweet(
            tweet_id=tweet_id,
            username=username,
            original_text=text,
            tweet_url=tweet_url,
            published_at=published_at,
        )

    async def fetch_tweets(self, username: str) -> list[Tweet]:
        """
        Berilgan username uchun tweetlarni oladi.

        Fallback chain: birinchi ishlaydigan Nitter instance'dan oladi.

        Args:
            username: X username (@ siz).

        Returns:
            Tweetlar ro'yxati (yangilardan eskiga).
        """
        rss_text: str | None = None

        # Fallback chain bo'ylab yurib chiqish
        for instance in self.instances:
            rss_text = await self._fetch_rss(instance, username)
            if rss_text:
                logger.info(
                    "Fetcher: %s uchun %s instance ishlatildi",
                    username, instance.url,
                )
                break

        if not rss_text:
            logger.error("Fetcher: %s uchun hech bir Nitter instance ishlamadi", username)
            return []

        # RSS ni parse qilish
        feed = feedparser.parse(rss_text)

        if feed.bozo:
            logger.warning(
                "Fetcher: RSS parse ogohlantirishlari mavjud (%s)",
                feed.bozo_exception,
            )

        tweets: list[Tweet] = []
        for entry in feed.entries:
            tweet = self._parse_entry(entry, username)
            if tweet:
                tweets.append(tweet)

        logger.info(
            "Fetcher: %s dan %d ta tweet olindi (%d ta entry dan)",
            username, len(tweets), len(feed.entries),
        )

        return tweets
