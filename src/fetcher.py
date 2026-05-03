"""
CyberWatch UZ Bot — Tweet Fetcher moduli.

Ushbu modul 2 ta usuldan foydalanadi:
1. Nitter RSS (nitter.net va boshqalar) - asosiy va tezkor usul.
2. Twikit - X ning ichki API si (agar RSS ishlamasa va cookies mavjud bo'lsa).
"""

import asyncio
from urllib.parse import unquote
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime
from pathlib import Path

import aiohttp
import feedparser
from twikit import Client

logger = logging.getLogger(__name__)

COOKIES_PATH = os.getenv("COOKIES_PATH", "data/cookies.json")

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.poast.org",
]


@dataclass
class Tweet:
    tweet_id: str
    username: str
    original_text: str
    tweet_url: str
    published_at: datetime
    image_url: str | None = None
    media_type: str = "photo"


class TweetFetcher:
    """Nitter RSS va Twikit orqali tweetlarni oluvchi gibrid klass."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._twikit_client: Client | None = None
        self._twikit_logged_in: bool = False

    async def start(self) -> None:
        """Sessiyalarni ochadi."""
        # 1. aiohttp sessiyasi (RSS uchun)
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        logger.info("Fetcher: HTTP sessiyasi ochildi (RSS uchun)")

        # 2. Twikit client (Fallback uchun)
        self._twikit_client = Client("en-US")
        cookies_file = Path(COOKIES_PATH)

        if cookies_file.exists():
            try:
                self._twikit_client.load_cookies(str(cookies_file))
                self._twikit_logged_in = True
                logger.info("Fetcher: Twikit cookies yuklandi")
            except Exception as e:
                logger.warning("Fetcher: Twikit cookies yuklanmadi: %s", str(e))
        else:
            logger.info("Fetcher: Twikit cookies yo'q, avval RSS sinab ko'riladi.")

    async def close(self) -> None:
        """Resurslarni tozalaydi."""
        if self._session:
            await self._session.close()
            self._session = None
        self._twikit_client = None
        self._twikit_logged_in = False
        logger.info("Fetcher: resurslar yopildi")

    # ==========================================
    # RSS qismi
    # ==========================================
    async def _fetch_rss(self, username: str) -> list[Tweet] | None:
        """RSS orqali tweetlarni olish. Xato bo'lsa None qaytaradi."""
        for instance in NITTER_INSTANCES:
            url = f"{instance}/{username}/rss"
            try:
                if not self._session:
                    break

                async with self._session.get(url) as response:
                    logger.info("Fetcher: %s HTTP Status: %s", url, response.status)
                    if response.status == 200:
                        text = await response.text()

                        if "<?xml" not in text[:50]:
                            continue

                        feed = feedparser.parse(text)

                        if feed.bozo:
                            if "not well-formed" in str(feed.bozo_exception):
                                continue

                        tweets = []
                        for entry in feed.entries:
                            tweet = self._parse_rss_entry(entry, username)
                            if tweet:
                                tweets.append(tweet)

                        logger.info("Fetcher: @%s dan %d ta tweet olindi (RSS: %s)", username, len(tweets), instance)
                        return tweets
            except BaseException as e:
                logger.warning("Fetcher: %s RSS xatosi: %s", instance, type(e).__name__)
                continue

        return None

    def _parse_rss_entry(self, entry: feedparser.FeedParserDict, username: str) -> Tweet | None:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        text = title if title else summary

        # Rasmni izlash — ham title ham summary dan barcha img taglarni topamiz
        image_url = None
        media_type = "photo"
        search_text = (title if title else "") + summary

        # Avval videolarni qidiramiz
        video_tags = re.findall(r'<video[^>]+[^>]+>', search_text) + re.findall(r'<source[^>]+src=["\']([^"\']+)["\']', search_text)
        for src in video_tags:
            src_url = src if isinstance(src, str) and not src.startswith("<") else ""
            if not src_url:
                src_match = re.search(r'data-url=["\']([^"\']+)["\']|src=["\']([^"\']+)["\']', src)
                if src_match:
                    src_url = src_match.group(1) or src_match.group(2)
            
            if src_url and "/pic/" in src_url:
                pic_part = re.search(r'/pic/(.+)', src_url)
                if pic_part:
                    decoded = unquote(pic_part.group(1))
                    if ".mp4" in decoded:
                        image_url = f"https://{decoded}"
                        media_type = "video"
                        break

        # Agar video topilmasa, rasmlarni qidiramiz
        if not image_url:
            img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', search_text)

            for src in img_tags:
                # Relative URL larni to'g'irlash
                if src.startswith("/"):
                    base_url = "/".join(entry.get("link", "").split("/")[:3])
                    src = base_url + src

                # Nitter /pic/ proxy URL larini haqiqiy pbs.twimg.com URL ga aylantirish
                if "/pic/" in src:
                    pic_part = re.search(r'/pic/(.+)', src)
                    if not pic_part:
                        continue
                    decoded = unquote(pic_part.group(1))

                    if decoded.startswith("media/"):
                        # Rasm URL: pbs.twimg.com/media/...jpg
                        # Ba'zan `?format=jpg&name=...` qo'shish kerak
                        if "?" not in decoded:
                            decoded = decoded + "?format=jpg&name=large"
                        image_url = f"https://pbs.twimg.com/{decoded}"
                        break  # Birinchi rasmni olib chiqamiz

                    elif decoded.startswith("tweet_video_thumb/"):
                        # Video thumbnail: pbs.twimg.com/tweet_video_thumb/...
                        image_url = f"https://pbs.twimg.com/{decoded}"
                        break

                    elif decoded.startswith("card_img/"):
                        # Card rasmlari - faqat format=jpg versiyasini olamiz (& muammosiz)
                        # card_img/ID/HASH?format=jpg&name=800x419 -> format=jpg&name=medium ishlatamiz
                        base_card = decoded.split("?")[0]  # Parametrlarsiz ID/HASH qismi
                        image_url = f"https://pbs.twimg.com/{base_card}?format=jpg&name=medium"
                        # card_img dan ko'ra to'g'ridan-to'g'ri rasm bo'lsa, uni afzal ko'ramiz
                        # shuning uchun break qilmaymiz, davom qilamiz
                        continue

                elif src.startswith("http") and any(ext in src for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                    # To'g'ridan-to'g'ri rasm URL
                    image_url = src
                    if ".gif" in src:
                        media_type = "animation"
                    break

        text = re.sub(r"<[^>]+>", "", title if title else summary).strip()
        if not text:
            return None

        if self._is_retweet_or_reply_text(text):
            return None

        tweet_id = entry.get("id", entry.get("link", ""))
        tweet_url = entry.get("link", "")

        published = entry.get("published_parsed")
        if published:
            published_at = datetime.fromtimestamp(mktime(published), tz=timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)

        return Tweet(
            tweet_id=tweet_id,
            username=username,
            original_text=text,
            tweet_url=tweet_url,
            published_at=published_at,
            image_url=image_url,
            media_type=media_type,
        )

    def _is_retweet_or_reply_text(self, text: str) -> bool:
        stripped = text.strip()
        if stripped.startswith("RT @") or stripped.startswith("@"):
            return True
        return False

    # ==========================================
    # Twikit qismi
    # ==========================================
    async def _fetch_twikit(self, username: str) -> list[Tweet]:
        """Twikit orqali tweetlarni olish."""
        if not self._twikit_client or not self._twikit_logged_in:
            # RSS ham ishlamasa va cookies yo'q bo'lsa, login qilib ko'ramiz
            success = await self._do_twikit_login()
            if not success:
                return []

        try:
            user = await self._twikit_client.get_user_by_screen_name(username)
            if not user:
                return []

            raw_tweets = await self._twikit_client.get_user_tweets(user.id, tweet_type="Tweets", count=10)
            tweets = []
            for raw_tweet in raw_tweets:
                tweet = self._parse_twikit_tweet(raw_tweet, username)
                if tweet:
                    tweets.append(tweet)
                    
            logger.info("Fetcher: @%s dan %d ta tweet olindi (Twikit)", username, len(tweets))
            return tweets
        except Exception as e:
            logger.warning("Fetcher: Twikit orqali olish xatosi: %s", str(e))
            return []

    async def _do_twikit_login(self) -> bool:
        """Twikit login qiladi (KEY_BYTE xatolari sababli faqat fallback sifatida)."""
        username = os.getenv("X_USERNAME", "").lstrip("@")
        email = os.getenv("X_EMAIL", "")
        password = os.getenv("X_PASSWORD", "")

        if not all([username, email, password]):
            return False

        try:
            logger.info("Fetcher: Twikit orqali X ga login qilinmoqda...")
            if self._twikit_client:
                await self._twikit_client.login(auth_info_1=username, auth_info_2=email, password=password)
                
                cookies_file = Path(COOKIES_PATH)
                cookies_file.parent.mkdir(parents=True, exist_ok=True)
                self._twikit_client.save_cookies(str(cookies_file))
                self._twikit_logged_in = True
                logger.info("Fetcher: Twikit login muvaffaqiyatli")
                return True
        except Exception as e:
            logger.warning("Fetcher: Twikit login muvaffaqiyatsiz (hozirda Twikit da KEY_BYTE muammosi mavjud bo'lishi mumkin): %s", str(e))
        
        return False

    def _parse_twikit_tweet(self, tweet_obj: object, username: str) -> Tweet | None:
        text = getattr(tweet_obj, "text", "") or ""
        full_text = getattr(tweet_obj, "full_text", "") or ""
        content = full_text if full_text else text

        if not content.strip():
            return None

        # RT/Reply check
        if getattr(tweet_obj, "in_reply_to_tweet_id", None) or self._is_retweet_or_reply_text(content):
            return None

        image_url = None
        media_type = "photo"
        media = getattr(tweet_obj, "media", [])
        if media and isinstance(media, list) and len(media) > 0:
            media_item = media[0]
            m_type = getattr(media_item, "type", "")
            if m_type == "video":
                media_type = "video"
                variants = getattr(media_item, "video_info", {}).get("variants", [])
                if variants:
                    # Get highest bitrate mp4
                    mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
                    if mp4s:
                        mp4s.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                        image_url = mp4s[0].get("url")
            elif m_type == "animated_gif":
                media_type = "animation"
                variants = getattr(media_item, "video_info", {}).get("variants", [])
                if variants:
                    image_url = variants[0].get("url")
            
            if not image_url:
                image_url = getattr(media_item, "media_url_https", None)

        tweet_id = str(getattr(tweet_obj, "id", ""))
        tweet_url = f"https://x.com/{username}/status/{tweet_id}"
        
        created_at = getattr(tweet_obj, "created_at", None)
        if isinstance(created_at, str):
            try:
                published_at = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            except ValueError:
                published_at = datetime.now(timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)

        return Tweet(
            tweet_id=tweet_id,
            username=username,
            original_text=content,
            tweet_url=tweet_url,
            published_at=published_at,
            image_url=image_url,
            media_type=media_type,
        )

    # ==========================================
    # Asosiy funksiya
    # ==========================================
    async def fetch_tweets(self, username: str) -> list[Tweet]:
        """
        Kanal tweetlarini olish uchun gibrid mantiq:
        1-o'rinda Nitter RSS (eng stabil).
        2-o'rinda Twikit (agar RSS larning hammasi o'lgan bo'lsa).
        """
        # 1. RSS
        tweets = await self._fetch_rss(username)
        if tweets is not None:
            return tweets
            
        # 2. Twikit Fallback
        logger.warning("Fetcher: Barcha RSS instance'lar band yoki ishlamayapti. Twikit fallback ishga tushirildi...")
        tweets = await self._fetch_twikit(username)
        
        return tweets
