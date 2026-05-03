"""
CyberWatch UZ Bot — Telegram poster moduli.

Tarjima qilingan postlarni Telegram kanalga yuboradi.
MarkdownV2 formatida, 4096 belgi limitini hisobga olgan holda.
"""

import logging
import re

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Telegram xabar limiti
TELEGRAM_MAX_LENGTH = 4096


def escape_markdown_v2(text: str) -> str:
    """
    MarkdownV2 uchun maxsus belgilarni escape qiladi.

    Telegram MarkdownV2 da quyidagi belgilar escape bo'lishi kerak:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def format_post(
    emoji: str,
    source_name: str,
    translated_text: str,
    tweet_url: str,
    published_at: str,
) -> str:
    """
    Telegram uchun post formatlaydi (MarkdownV2).

    Args:
        emoji: Manba kanali emojisi.
        source_name: Manba kanali nomi.
        translated_text: Tarjima qilingan matn.
        tweet_url: Asl tweet URL.
        published_at: Nashr vaqti (string).

    Returns:
        Formatlangan MarkdownV2 xabar.
    """
    safe_name = escape_markdown_v2(source_name)
    safe_text = escape_markdown_v2(translated_text)
    safe_time = escape_markdown_v2(published_at)
    safe_url = tweet_url.replace(")", "\\)")  # URL dagi maxsus belgilar

    message = (
        f"{emoji} *{safe_name}*\n\n"
        f"{safe_text}\n\n"
        f"🔗 [Asl manba]({safe_url})\n"
        f"🕐 {safe_time} \\| \\#cybersecurity \\#uzbekistan"
    )
    return message


def split_long_message(message: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """
    Uzun xabarni ikki qismga bo'ladi.

    Args:
        message: To'liq xabar matni.
        max_length: Maksimal belgilar soni.

    Returns:
        Xabar qismlari ro'yxati.
    """
    if len(message) <= max_length:
        return [message]

    # Birinchi qismni max_length gacha, oxirgi yangi qator joyidan kesish
    split_point = message.rfind("\n", 0, max_length - 20)
    if split_point == -1:
        split_point = max_length - 20

    part1 = message[:split_point] + "\n\n⬇️ _davomi\\.\\.\\._"
    part2 = "⬆️ _davomi_\n\n" + message[split_point:]

    # Ikkinchi qism ham uzun bo'lsa, kesib qo'yish
    if len(part2) > max_length:
        part2 = part2[:max_length - 10] + "\\.\\.\\."

    return [part1, part2]


class TelegramPoster:
    """Telegram kanalga post yuboruvchi klass."""

    def __init__(self, bot_token: str, channel_id: str) -> None:
        self.bot = Bot(token=bot_token)
        self.channel_id = channel_id

    async def send_startup_message(self) -> None:
        """Bot ishga tushganini bildiruvchi xabar yuboradi."""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text="✅ *CyberWatch UZ Bot ishga tushdi*\n\n"
                     "Kanallarni kuzatish boshlandi\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            logger.info("Startup xabari Telegram ga yuborildi")
        except TelegramError as e:
            logger.error("Startup xabarini yuborishda xato: %s", str(e))

    async def send_post(
        self,
        emoji: str,
        source_name: str,
        translated_text: str,
        tweet_url: str,
        published_at: str,
    ) -> bool:
        """
        Bitta postni Telegram kanalga yuboradi.

        Args:
            emoji: Manba emojisi.
            source_name: Manba nomi.
            translated_text: Tarjima qilingan matn.
            tweet_url: Asl tweet URL.
            published_at: Nashr vaqti.

        Returns:
            True agar muvaffaqiyatli yuborilsa.
        """
        try:
            message = format_post(
                emoji=emoji,
                source_name=source_name,
                translated_text=translated_text,
                tweet_url=tweet_url,
                published_at=published_at,
            )

            parts = split_long_message(message)

            for i, part in enumerate(parts):
                try:
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=part,
                        parse_mode=ParseMode.MARKDOWN_V2,
                        disable_web_page_preview=True,
                    )
                    logger.debug("Post qismi %d/%d yuborildi", i + 1, len(parts))
                except TelegramError as e:
                    # MarkdownV2 xatosi bo'lsa, oddiy matn sifatida yuborish
                    logger.warning("MarkdownV2 xatosi, oddiy matn yuborilmoqda: %s", str(e))
                    plain_text = re.sub(r"\\(.)", r"\1", part)
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=plain_text,
                        disable_web_page_preview=True,
                    )

            logger.info("Post yuborildi: %s — %s", source_name, tweet_url)
            return True

        except TelegramError as e:
            logger.error("Telegram xatosi: %s (post: %s)", str(e), tweet_url)
            return False
        except Exception as e:
            logger.error("Kutilmagan xato post yuborishda: %s", str(e))
            return False
