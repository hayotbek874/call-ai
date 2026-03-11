import os

PROJECT = "/Users/shaxzodbek/PycharmProjects/STRATIX_AI_CHAT_BOT"
files = {}

# ============================================================
# SERVICES - VOICE
# ============================================================

files["src/services/voice/tts_service.py"] = """\
from collections.abc import AsyncIterator

from src.clients.openai_client import OpenAIClient


class TTSService:
    def __init__(self, openai_client: OpenAIClient):
        self._openai = openai_client

    async def synthesize_stream(self, text: str, language: str) -> AsyncIterator[bytes]:
        async for chunk in self._openai.tts_stream(text, language):
            yield chunk
"""

files["src/services/voice/stt_service.py"] = """\
from src.clients.openai_client import OpenAIClient


class STTService:
    def __init__(self, openai_client: OpenAIClient):
        self._openai = openai_client

    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        return await self._openai.transcribe(audio_bytes, language)
"""

files["src/services/voice/vad_service.py"] = """\
import audioop
from collections.abc import AsyncIterator


class VADService:
    def __init__(self, silence_threshold: int = 500, silence_duration_ms: int = 700,
                 sample_rate: int = 16000, chunk_ms: int = 20):
        self._threshold = silence_threshold
        self._silence_chunks = silence_duration_ms // chunk_ms
        self._sample_rate = sample_rate
        self._chunk_ms = chunk_ms

    def is_speech(self, pcm_chunk: bytes) -> bool:
        rms = audioop.rms(pcm_chunk, 2)
        return rms > self._threshold

    async def detect_utterances(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        buffer = bytearray()
        silence_count = 0
        speaking = False
        async for chunk in audio_stream:
            if self.is_speech(chunk):
                speaking = True
                silence_count = 0
                buffer.extend(chunk)
            elif speaking:
                silence_count += 1
                buffer.extend(chunk)
                if silence_count >= self._silence_chunks:
                    yield bytes(buffer)
                    buffer.clear()
                    speaking = False
                    silence_count = 0
"""

files["src/services/voice/__init__.py"] = """\
from src.services.voice.stt_service import STTService
from src.services.voice.tts_service import TTSService
from src.services.voice.vad_service import VADService

__all__ = ["STTService", "TTSService", "VADService"]
"""

# ============================================================
# SERVICES - AI
# ============================================================

files["src/services/ai/intent_service.py"] = """\
import re

LOT_PATTERN = re.compile(r"\\b[A-Z]{1,3}[0-9]{2,5}\\b")

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
    def detect_keyword(self, text: str) -> str:
        lower = text.lower()
        if LOT_PATTERN.search(text.upper()):
            return "lot_number"
        for intent, words in KEYWORDS.items():
            if any(w in lower for w in words):
                return intent
        return "fallback"

    def extract_lot(self, text: str) -> str | None:
        match = LOT_PATTERN.search(text.upper())
        return match.group(0) if match else None
"""

files["src/services/ai/prompt_builder.py"] = '''\
_SYSTEM_RU = """\\u0422\\u044b \\u2014 AI \\u043e\\u043f\\u0435\\u0440\\u0430\\u0442\\u043e\\u0440 ZargarShop, \\u044e\\u0432\\u0435\\u043b\\u0438\\u0440\\u043d\\u043e\\u0433\\u043e \\u0442\\u0435\\u043b\\u0435\\u043c\\u0430\\u0433\\u0430\\u0437\\u0438\\u043d\\u0430 \\u0432 \\u0423\\u0437\\u0431\\u0435\\u043a\\u0438\\u0441\\u0442\\u0430\\u043d\\u0435.
\\u042f\\u0437\\u044b\\u043a: \\u0440\\u0443\\u0441\\u0441\\u043a\\u0438\\u0439 \\u0438\\u043b\\u0438 \\u0443\\u0437\\u0431\\u0435\\u043a\\u0441\\u043a\\u0438\\u0439 \\u2014 \\u0438\\u0441\\u043f\\u043e\\u043b\\u044c\\u0437\\u0443\\u0439 \\u044f\\u0437\\u044b\\u043a \\u043a\\u043b\\u0438\\u0435\\u043d\\u0442\\u0430. \\u041c\\u0430\\u043a\\u0441\\u0438\\u043c\\u0443\\u043c 2 \\u043f\\u0440\\u0435\\u0434\\u043b\\u043e\\u0436\\u0435\\u043d\\u0438\\u044f. \\u0417\\u0430\\u043a\\u0430\\u043d\\u0447\\u0438\\u0432\\u0430\\u0439 \\u0432\\u043e\\u043f\\u0440\\u043e\\u0441\\u043e\\u043c.
\\u041d\\u0435 \\u0432\\u044b\\u0445\\u043e\\u0434\\u0438 \\u0437\\u0430 \\u0442\\u0435\\u043c\\u0443 \\u0443\\u043a\\u0440\\u0430\\u0448\\u0435\\u043d\\u0438\\u0439 \\u0438 \\u0437\\u0430\\u043a\\u0430\\u0437\\u043e\\u0432.

{product_context}
{summary_block}"""

_SYSTEM_UZ = """Siz \\u2014 ZargarShop, O\\u2018zbekistondagi zargarlik telefon-do\\u2018konining AI operatoriSIZ.
Til: o\\u2018zbek yoki rus \\u2014 mijoz qaysi tilda yozsa shu tilda javob bering. Maksimum 2 jumla. Savol bilan tugating.
Zargarlik va buyurtmadan tashqari mavzularga kirmaslik.

{product_context}
{summary_block}"""


def build_system_prompt(language: str, summary: str | None, product_context: str | None) -> str:
    template = _SYSTEM_RU if language == "ru" else _SYSTEM_UZ
    summary_block = f"\\nPREVIOUS CONTEXT: {summary}" if summary else ""
    product_block = product_context or ""
    return template.format(summary_block=summary_block, product_context=product_block)
'''

files["src/services/ai/product_search_service.py"] = """\
from redis.asyncio import Redis

from src.clients.product_api_client import ProductAPIClient


class ProductSearchService:
    CACHE_KEY = "product:{lot}"
    TTL = 300

    def __init__(self, client: ProductAPIClient, redis: Redis):
        self._client = client
        self._redis = redis

    async def search_by_lot(self, lot: str | None) -> str | None:
        if not lot:
            return None
        key = self.CACHE_KEY.format(lot=lot)
        cached = await self._redis.get(key)
        if cached:
            return cached if isinstance(cached, str) else cached.decode()
        product = await self._client.search_by_lot(lot)
        if not product:
            return None
        text = (
            f"Lot: {product.lot} | {product.name_ru} / {product.name_uz} | "
            f"\\u041e\\u043f\\u0438\\u0441\\u0430\\u043d\\u0438\\u0435: {product.description_ru} | "
            f"\\u041f\\u043e\\u043b\\u043d\\u0430\\u044f \\u0446\\u0435\\u043d\\u0430: {product.full_price:,} \\u0441\\u0443\\u043c | "
            f"\\u0410\\u043a\\u0446\\u0438\\u043e\\u043d\\u043d\\u0430\\u044f \\u0446\\u0435\\u043d\\u0430: {product.sale_price:,} \\u0441\\u0443\\u043c | "
            f"\\u0412 \\u043d\\u0430\\u043b\\u0438\\u0447\\u0438\\u0438: {product.stock} \\u0448\\u0442 | "
            f"\\u0420\\u0430\\u0437\\u043c\\u0435\\u0440\\u044b: {\\', \\'.join(product.sizes) if product.sizes else \\u0027\\u0443\\u0442\\u043e\\u0447\\u043d\\u0438\\u0442\\u044c\\u0027}"
        )
        await self._redis.setex(key, self.TTL, text)
        return text
"""

files["src/services/ai/__init__.py"] = """\
from src.services.ai.chat_orchestrator import ChatOrchestrator
from src.services.ai.context_service import ContextService
from src.services.ai.intent_service import IntentService
from src.services.ai.product_search_service import ProductSearchService
from src.services.ai.prompt_builder import build_system_prompt

__all__ = [
    "ChatOrchestrator",
    "ContextService",
    "IntentService",
    "ProductSearchService",
    "build_system_prompt",
]
"""

for path, content in files.items():
    full_path = os.path.join(PROJECT, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    print(f"wrote {path}")
