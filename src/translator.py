"""
CyberWatch UZ Bot — Tarjima moduli.

Google Gemini 1.5 Flash orqali inglizcha matnni
O'zbek tiliga tarjima qiladi.
"""

import asyncio
import logging

import google.generativeai as genai

logger = logging.getLogger(__name__)

# System prompt
SYSTEM_PROMPT = """Sen kiberxavfsizlik sohasidagi professional tarjimonsan.
Berilgan inglizcha xabarni O'zbek tiliga tarjima qil.

QOIDALAR:
- Texnik atamalarni (CVE, RCE, XSS, SQLi va h.k.) tarjima qilma, asl holatida qoldir
- Kompaniya nomlari, mahsulot nomlari o'zgarmaydi
- Tarjima tabiiy va tushunarli bo'lsin
- Faqat tarjimani ber, hech qanday izoh yoki qo'shimcha so'z yozma
- Agar matn allaqachon O'zbekcha yoki Ruscha bo'lsa, O'zbekchaga o'gir"""


class Translator:
    """Gemini AI orqali tarjima qiluvchi klass."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._model: genai.GenerativeModel | None = None
        self._max_retries: int = 3
        self._base_delay: float = 2.0  # sekundlarda

    def setup(self) -> None:
        """Gemini API ni sozlaydi."""
        genai.configure(api_key=self.api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
        )
        logger.info("Gemini tarjima modeli sozlandi (gemini-1.5-flash)")

    async def translate(self, text: str) -> str:
        """
        Matnni O'zbek tiliga tarjima qiladi.

        Exponential backoff bilan retry qiladi.
        Xato bo'lsa original matnni qaytaradi.

        Args:
            text: Tarjima qilinadigan matn.

        Returns:
            Tarjima qilingan matn (yoki original, xato bo'lsa).
        """
        if not self._model:
            raise RuntimeError("Model sozlanmagan. setup() ni chaqiring.")

        if not text.strip():
            return text

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await asyncio.to_thread(
                    self._model.generate_content,
                    text,
                )

                if response and response.text:
                    translated = response.text.strip()
                    logger.debug(
                        "Tarjima muvaffaqiyatli (attempt %d): %s... → %s...",
                        attempt,
                        text[:50],
                        translated[:50],
                    )
                    return translated
                else:
                    logger.warning(
                        "Tarjima: bo'sh javob (attempt %d/%d)",
                        attempt, self._max_retries,
                    )

            except Exception as e:
                delay = self._base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Tarjima xatosi (attempt %d/%d): %s — %0.1fs kutilmoqda",
                    attempt, self._max_retries, str(e), delay,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(delay)

        # Barcha urinishlar muvaffaqiyatsiz — original matnni qaytarish
        logger.error(
            "Tarjima amalga oshmadi (%d urinish). Original matn qaytarilmoqda: %s...",
            self._max_retries,
            text[:80],
        )
        return text
