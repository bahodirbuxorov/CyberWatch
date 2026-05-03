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


import html

def format_post(
    emoji: str,
    source_name: str,
    translated_text: str,
    tweet_url: str,
    published_at: str,
) -> str:
    """
    Telegram uchun post formatlaydi (HTML).
    """
    safe_name = html.escape(source_name)
    # Gemini dan kelgan tekstda allaqachon HTML bor deb hisoblaymiz
    safe_text = translated_text
    safe_time = html.escape(published_at)

    message = (
        f"{emoji} <b>{safe_name}</b>\n\n"
        f"{safe_text}\n\n"
        f"🕐 {safe_time} | #cybersecurity #uzbekistan"
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
        image_url: str | None = None,
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
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        try:
            message = format_post(
                emoji=emoji,
                source_name=source_name,
                translated_text=translated_text,
                tweet_url=tweet_url,
                published_at=published_at,
            )

            parts = split_long_message(message)
            
            # Button faqat oxirgi xabarga qo'shiladi
            keyboard = [[InlineKeyboardButton("🔗 Asl manbaga o'tish", url=tweet_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                current_markup = reply_markup if is_last else None

                try:
                    # Rasm bormi va bu birinchi qismmi?
                    if image_url and i == 0 and len(part) <= 1024:
                        await self.bot.send_photo(
                            chat_id=self.channel_id,
                            photo=image_url,
                            caption=part,
                            parse_mode=ParseMode.HTML,
                            reply_markup=current_markup,
                        )
                    else:
                        await self.bot.send_message(
                            chat_id=self.channel_id,
                            text=part,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True,
                            reply_markup=current_markup,
                        )
                    logger.debug("Post qismi %d/%d yuborildi", i + 1, len(parts))
                except TelegramError as e:
                    # Rasm yuborishda xato bo'lsa yoki HTML xato ketsa, matn bilan yuboramiz
                    logger.warning("HTML yoki rasm xatosi: %s", str(e))
                    # Agar rasm xatosi bo'lgan bo'lsa, xabarning o'zini yuborib ko'ramiz
                    # HTML parser xatosi bo'lishi ham mumkin, shuning uchun matnni escape qilamiz
                    plain_text = html.escape(part)
                    await self.bot.send_message(
                        chat_id=self.channel_id,
                        text=plain_text,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                        reply_markup=current_markup,
                    )

            logger.info("Post yuborildi: %s — %s", source_name, tweet_url)
            return True

        except TelegramError as e:
            logger.error("Telegram xatosi: %s (post: %s)", str(e), tweet_url)
            return False
        except Exception as e:
            logger.error("Kutilmagan xato post yuborishda: %s", str(e))
            return False
