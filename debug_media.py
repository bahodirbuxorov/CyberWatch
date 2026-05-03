import asyncio
import aiohttp
import feedparser
import re
from urllib.parse import unquote

def extract_image_url(entry):
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    search_text = title + summary
    image_url = None

    img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', search_text)
    for src in img_tags:
        if src.startswith("/"):
            base_url = "/".join(entry.get("link", "").split("/")[:3])
            src = base_url + src

        if "/pic/" in src:
            pic_part = re.search(r'/pic/(.+)', src)
            if not pic_part:
                continue
            decoded = unquote(pic_part.group(1))

            if decoded.startswith("media/"):
                if "?" not in decoded:
                    decoded = decoded + "?format=jpg&name=large"
                image_url = f"https://pbs.twimg.com/{decoded}"
                break
            elif decoded.startswith("tweet_video_thumb/"):
                image_url = f"https://pbs.twimg.com/{decoded}"
                break
            elif decoded.startswith("card_img/"):
                base_card = decoded.split("?")[0]
                image_url = f"https://pbs.twimg.com/{base_card}?format=jpg&name=medium"
                continue
        elif src.startswith("http") and any(ext in src for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            image_url = src
            break

    return image_url

async def debug():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        for feed_url in [
            'https://nitter.net/DarkWebInformer/rss',
            'https://nitter.net/DailyDarkWeb/rss',
            'https://nitter.net/VECERTRadar/rss',
        ]:
            print(f"\n=== {feed_url.split('/')[3]} ===")
            async with session.get(feed_url) as r:
                text = await r.text()
                feed = feedparser.parse(text)
                img_count = 0
                no_img_count = 0
                for entry in feed.entries[:15]:
                    url = extract_image_url(entry)
                    if url:
                        img_count += 1
                        print(f"  ✅ {url[:80]}")
                    else:
                        no_img_count += 1
                print(f"\n  Rasm bor: {img_count} | Rasm yo'q: {no_img_count}")

asyncio.run(debug())
