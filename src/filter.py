"""
CyberWatch UZ Bot — Keyword filter moduli.

DeepTechTR kanalidan kelgan postlarni IT/Cybersecurity
mavzusiga oid ekanligini tekshiradi.
"""

import logging

logger = logging.getLogger(__name__)

# Kiberxavfsizlik kalit so'zlari (kichik harfda)
CYBER_KEYWORDS: set[str] = {
    "vulnerability",
    "cve",
    "exploit",
    "breach",
    "hack",
    "malware",
    "ransomware",
    "phishing",
    "zero-day",
    "0day",
    "patch",
    "security",
    "cyber",
    "threat",
    "attack",
    "backdoor",
    "botnet",
    "trojan",
    "spyware",
    "data leak",
    "cisa",
    "nvd",
    "cvss",
    "apt",
    "ddos",
    "injection",
    "xss",
    "rce",
    "privilege escalation",
}


def is_cyber_related(text: str) -> bool:
    """
    Matn kiberxavfsizlikga oid ekanligini tekshiradi.

    Kalit so'zlardan kamida BITTASI topilsa True qaytaradi.
    Tekshiruv case-insensitive.

    Args:
        text: Tekshiriladigan matn.

    Returns:
        True agar matn kiberxavfsizlikga oid bo'lsa.
    """
    text_lower = text.lower()
    for keyword in CYBER_KEYWORDS:
        if keyword in text_lower:
            logger.debug("Filter: '%s' kalit so'zi topildi", keyword)
            return True

    logger.debug("Filter: hech qanday kiberxavfsizlik kalit so'zi topilmadi")
    return False
