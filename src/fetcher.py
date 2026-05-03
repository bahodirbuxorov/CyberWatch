"""
CyberWatch UZ Bot — Tweet Fetcher moduli.

Twikit kutubxonasi orqali X (Twitter) dan tweetlarni oladi.
Nitter endi ishlamaganligi sababli, twikit X ning ichki API si
orqali ishlaydi (Twitter API key kerak emas, faqat X account).
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from twikit import Client

logger = logging.getLogger(__name__)

# Cookies faylining joylashuvi
COOKIES_PATH = os.getenv("COOKIES_PATH", "data/cookies.json")


@dataclass
class Tweet:
    """Bitta tweet ma'lumotlari."""
    tweet_id: str
    username: str
    original_text: str
    tweet_url: str
    published_at: datetime


class TweetFetcher:
    """Twikit orqali X dan tweetlarni oluvchi klass."""

    def __init__(self) -> None:
        self._client: Client | None = None
        self._logged_in: bool = False

    async def start(self) -> None:
        """X ga ulanadi va login qiladi."""
        self._client = Client("en-US")

        cookies_file = Path(COOKIES_PATH)

        # Oldingi sessiyadan cookies mavjud bo'lsa, yuklash
        if cookies_file.exists():
            try:
                self._client.load_cookies(str(cookies_file))
                self._logged_in = True
                logger.info("Fetcher: cookies fayldan yuklandi (%s)", COOKIES_PATH)
                return
            except Exception as e:
                logger.warning("Fetcher: cookies yuklanmadi, qayta login: %s", str(e))

        # Yangi login qilish
        username = os.getenv("X_USERNAME", "")
        email = os.getenv("X_EMAIL", "")
        password = os.getenv("X_PASSWORD", "")

        if not all([username, email, password]):
            logger.error(
                "Fetcher: X_USERNAME, X_EMAIL va X_PASSWORD .env da bo'lishi kerak!"
            )
            return

        try:
            await self._client.login(
                auth_info_1=username,
                auth_info_2=email,
                password=password,
            )
            # Cookies ni saqlash (keyingi ishga tushirishlar uchun)
            cookies_dir = cookies_file.parent
            cookies_dir.mkdir(parents=True, exist_ok=True)
            self._client.save_cookies(str(cookies_file))
            self._logged_in = True
            logger.info("Fetcher: X ga muvaffaqiyatli login qilindi va cookies saqlandi")
        except Exception as e:
            logger.error("Fetcher: X ga login xatosi: %s", str(e))
            self._logged_in = False

    async def close(self) -> None:
        """Resurslarni tozalaydi."""
        self._client = None
        self._logged_in = False
        logger.info("Fetcher: yopildi")

    def _is_retweet_or_reply(self, tweet_obj: object) -> bool:
        """Retweet yoki Reply ekanligini tekshiradi."""
        text = getattr(tweet_obj, "text", "") or ""
        # Retweet
        if text.strip().startswith("RT @"):
            return True
        # Reply (in_reply_to mavjud bo'lsa)
        if getattr(tweet_obj, "in_reply_to_tweet_id", None):
            return True
        # @ bilan boshlanuvchi reply
        if text.strip().startswith("@"):
            return True
        return False

    def _parse_tweet(self, tweet_obj: object, username: str) -> Tweet | None:
        """
        Twikit tweet obyektini bizning Tweet dataclass ga o'giradi.

        Args:
            tweet_obj: Twikit dan kelgan tweet.
            username: Manba kanal username.

        Returns:
            Tweet obyekti yoki None (filter qilinsa).
        """
        # Matnni olish
        text = getattr(tweet_obj, "text", "") or ""
        full_text = getattr(tweet_obj, "full_text", "") or ""
        content = full_text if full_text else text

        if not content.strip():
            return None

        # RT va Reply filtrlash
        if self._is_retweet_or_reply(tweet_obj):
            logger.debug("Fetcher: RT/Reply filtrlandi — %s...", content[:50])
            return None

        # Tweet ID
        tweet_id = str(getattr(tweet_obj, "id", ""))

        # Tweet URL
        tweet_url = f"https://x.com/{username}/status/{tweet_id}"

        # Vaqt
        created_at = getattr(tweet_obj, "created_at", None)
        if created_at and isinstance(created_at, str):
            try:
                # Twikit format: "Wed Oct 10 20:19:24 +0000 2018"
                published_at = datetime.strptime(
                    created_at, "%a %b %d %H:%M:%S %z %Y"
                )
            except ValueError:
                published_at = datetime.now(timezone.utc)
        elif isinstance(created_at, datetime):
            published_at = created_at
        else:
            published_at = datetime.now(timezone.utc)

        return Tweet(
            tweet_id=tweet_id,
            username=username,
            original_text=content,
            tweet_url=tweet_url,
            published_at=published_at,
        )

    async def fetch_tweets(self, username: str) -> list[Tweet]:
        """
        Berilgan username uchun tweetlarni oladi.

        Args:
            username: X username (@ siz).

        Returns:
            Tweetlar ro'yxati.
        """
        if not self._client or not self._logged_in:
            logger.error("Fetcher: X ga ulanilmagan. start() ni chaqiring.")
            return []

        try:
            # Foydalanuvchini topish
            user = await self._client.get_user_by_screen_name(username)
            if not user:
                logger.warning("Fetcher: @%s foydalanuvchisi topilmadi", username)
                return []

            logger.debug("Fetcher: @%s foydalanuvchisi topildi (id=%s)", username, user.id)

            # Tweetlarni olish
            raw_tweets = await self._client.get_user_tweets(
                user.id,
                tweet_type="Tweets",
                count=20,
            )

            tweets: list[Tweet] = []
            for raw_tweet in raw_tweets:
                tweet = self._parse_tweet(raw_tweet, username)
                if tweet:
                    tweets.append(tweet)

            logger.info(
                "Fetcher: @%s dan %d ta tweet olindi",
                username, len(tweets),
            )
            return tweets

        except Exception as e:
            logger.error("Fetcher: @%s dan tweet olishda xato: %s", username, str(e))

            # Agar authentication xatosi bo'lsa, qayta login qilishga urinish
            error_str = str(e).lower()
            if "unauthorized" in error_str or "403" in error_str or "auth" in error_str:
                logger.info("Fetcher: Auth xatosi — qayta login qilinmoqda...")
                await self._relogin()

            return []

    async def _relogin(self) -> None:
        """Cookies o'chirib qayta login qiladi."""
        cookies_file = Path(COOKIES_PATH)
        if cookies_file.exists():
            cookies_file.unlink()
            logger.info("Fetcher: eski cookies o'chirildi")

        # Biroz kutish (rate limit uchun)
        await asyncio.sleep(5)
        await self.start()
