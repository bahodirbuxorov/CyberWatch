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
SYSTEM_PROMPT = """Sen kiberxavfsizlik bo'yicha ekspert va Telegram kanali uchun professional kopiraytersan. 
Berilgan inglizcha xabarni tahlil qilib, 850 belgidan oshmaydigan eng yuqori sifatli O'zbekcha post tayyorla.

QAT'IY SHABLON (Aynan shu ketma-ketlikda yoz):
[Xavf darajasiga qarab bitta emoji: 🆘 KRITIK, ⚠️ DIQQAT yoki ℹ️ XABAR] <b>[QISQA VA JALB QILUVCHI SARLAVHA]</b>

📝 <b>Mohiyati:</b> [Asosiy voqea nima ekanligini 1-2 gapda, sodda tushuntir]

🎯 <b>Ta'siri:</b> [Kimga zarar yetishi mumkinligini yoz]

🛡️ <b>Nima qilish kerak?:</b> [Aniq 1-2 ta yechim yoki tavsiya]

#️⃣ [Mavzuga doir 3 ta inglizcha heshteg, masalan: #DataBreach #Ransomware #Privacy]

QOIDALAR:
- T.co yoki boshqa begona havolalarni (linklarni) umuman matnga qo'shma, tozalab tashla.
- Texnik so'zlar (SQLi, CVE, Phishing) asli qanday bo'lsa shunday qolsin.
- Ortiqcha salomlashish, kirish so'zlar yozma, to'g'ridan-to'g'ri shablonga o't.
- Matn HTML formatda va Telegramga mos bo'lsin."""


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
            model_name="gemini-flash-latest",
            system_instruction=SYSTEM_PROMPT,
        )
        logger.info("Gemini tarjima modeli sozlandi (gemini-flash-latest)")

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
