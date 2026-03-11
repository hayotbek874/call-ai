import re

from src.core.logging import get_logger

logger = get_logger(__name__)

LOT_PATTERN = re.compile(r"\b[A-Z]{1,3}[0-9]{2,5}\b")

KEYWORDS: dict[str, list[str]] = {
    "greeting": ["salom", "assalomu", "zdravstvuyte", "privet", "allo", "xayr"],
    "lot_number": [],
    "order_request": ["buyurtma", "zakaz", "olmoqchi", "kupit", "oformit", "xohliman"],
    "price_inquiry": ["narx", "tsena", "qancha", "skolko", "stoit"],
    "delivery_inquiry": ["yetkazib", "dostavka", "qachon", "kogda", "kak bystro"],
    "delivery_tashkent": ["tashkent", "toshkent"],
    "discount_inquiry": ["chegirma", "skidka", "aktsiya", "aktsii", "bonus"],
    "loyalty_card": ["premium", "chegirma klubi", "diskont karta", "club", "klubga"],
    "size_inquiry": ["razmer", "olcham", "razmer", "size"],
    "payment_inquiry": ["tolov", "oplata", "nalichnymi", "naqd", "click", "payme"],
    "guarantee_inquiry": ["kafolat", "garantiya", "obmen", "vozvrat"],
    "quality_inquiry": ["qoraya", "cherneet", "stiort", "polinaet"],
    "operator_request": ["operator", "odam", "chelovek", "menejer", "sotrudnik"],
    "farewell": ["rahmat", "spasibo", "xayr", "do svidaniya", "poka"],
    "confirm_order": ["ha", "da", "tasdiqladi", "oformlyaem", "soglasen"],
    "reject": ["yoq", "net", "ne nado", "otkazyvayus"],
}

class IntentService:
    async def detect_keyword(self, text: str) -> str:
        lower = text.lower()
        if LOT_PATTERN.search(text.upper()):
            await logger.debug("intent_detected", intent="lot_number", text_preview=text[:50])
            return "lot_number"
        for intent, words in KEYWORDS.items():
            if any(w in lower for w in words):
                await logger.debug("intent_detected", intent=intent, text_preview=text[:50])
                return intent
        await logger.debug("intent_fallback", text_preview=text[:50])
        return "fallback"

    async def extract_lot(self, text: str) -> str | None:
        match = LOT_PATTERN.search(text.upper())
        lot = match.group(0) if match else None
        if lot:
            await logger.debug("lot_extracted", lot=lot)
        return lot
