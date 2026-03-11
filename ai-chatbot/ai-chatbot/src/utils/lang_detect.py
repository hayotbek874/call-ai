import re

from src.core.logging import get_logger

logger = get_logger(__name__)

_RU_CHARS = set("ёЁцЦщЩъЪыЫэЭ")

_UZ_LATIN = re.compile(r"[a-zA-Z]{2,}")

_UZ_MARKERS = re.compile(
    r"(?:o'|g'|ʻ|sh|ch|"

    r"\bassalomu\b|\bsalom\b|\bxush\b|\brahmat\b|\biltimos\b|\bxayr\b|\bha\b|\byoq\b|"

    r"\bqancha\b|\bnarx\b|\byetkazib\b|\bbuyurtma\b|\bchegirma\b|\bkafolat\b|\bto'lov\b|"
    r"\boltin\b|\bkumush\b|\buzuk\b|\btaqinchoq\b|\bzeb\b|\bzargarlik\b|\bsirg'a\b|\bmarjon\b|"
    r"\bbilezik\b|\bzanjir\b|\bkulon\b|\btosh\b|\bolmos\b|"

    r"\bbo'lsa\b|\bqiling\b|\bberish\b|\bqiladi\b|\bkerak\b|\bboring\b|\bboladi\b|\bolish\b|"
    r"\bko'rish\b|\bko'rsating\b|\bolsam\b|\bberaman\b|\bber\b|\bqil\b|\byuborish\b|"
    r"\baytish\b|\bayt\b|\bkelish\b|\bketish\b|\bolaman\b|\bqilaman\b|"

    r"\bsizga\b|\bbizga\b|\bmenimcha\b|\bmen\b|\bsiz\b|\bnima\b|\bhaqida\b|\blot\b|"
    r"\bshunday\b|\bchiroyli\b|\bqanday\b|\bqaysi\b|\bbilan\b|\buchun\b|\bbu\b|\bu\b|"
    r"\bbor\b|\byo'q\b|\byuq\b|\bham\b|\bva\b|\byoki\b|\bagar\b|\blekin\b|"

    r"\bbormi\b|\byoqmi\b|\bqayerda\b|\bqachon\b|\bnega\b|\bnimaga\b|\bkim\b|"

    r"\bbitta\b|\bikkita\b|\buchta\b|\bto'rtta\b|\bbeshta\b|\bolta\b|\byetti\b|\bsakkiz\b|"
    r"\bming\b|\bso'm\b|\bsum\b|"

    r"\btoshkent\b|\bsamarqand\b|\bbuxoro\b|\bfarg'ona\b|\bandij\b|\bnamangan\b|"
    r"\bxorazm\b|\bnukus\b|\bqarshi\b|\btermiz\b|\bjizzax\b|\bnavoiy\b)",
    re.IGNORECASE,
)

_UZ_CYRILLIC_MARKERS = re.compile(
    r"(?:\bсалом\b|\bассалому\b|\bрахмат\b|\bилтимос\b|\bхайр\b|"
    r"\bқанча\b|\bнарх\b|\bбуюртма\b|\bкерак\b|\bбўлса\b|"
    r"\bменга\b|\bсизга\b|\bнима\b|\bқандай\b|\bқайси\b|"
    r"\bҳа\b|\bйўқ\b|\bбор\b|\bхўп\b|\bмайли\b)",
    re.IGNORECASE,
)

_RU_MARKERS = re.compile(
    r"(?:\bздравствуй|\bпривет|\bспасибо|\bпожалуйста|\bсколько|\bзаказ|"
    r"\bдоставк|\bскидк|\bгаранти|\bоплат|\bразмер|\bукрашени|"
    r"\bкарт|\bхочу|\bмне\b|\bвас\b|\bможно\b|\bкак\b|\bчто\b|\bэто\b|"

    r"\bзолот|\bсеребр|\bкольц|\bсерьг|\bбраслет|\bцепочк|"
    r"\bпокажите|\bрасскажите|\bесть\b|\bнет\b|\bда\b|"
    r"\bподскажите|\bпосмотреть|\bкупить|\bцена|\bстоит|"
    r"\bдорог|\bдешев|\bкачеств|\bподарок)",
    re.IGNORECASE,
)

_HAS_CYRILLIC = re.compile(r"[а-яА-ЯёЁ]")

async def detect_language(text: str) -> str:

    if not text or not text.strip():
        await logger.debug("lang_detect_empty_text")
        return "both"

    text_stripped = text.strip()

    uz_matches = _UZ_MARKERS.findall(text_stripped)
    uz_cyrillic_matches = _UZ_CYRILLIC_MARKERS.findall(text_stripped)
    ru_matches = _RU_MARKERS.findall(text_stripped)

    uz_score = len(uz_matches) + len(uz_cyrillic_matches)
    ru_score = len(ru_matches)

    latin_words = _UZ_LATIN.findall(text_stripped)
    has_cyrillic = bool(_HAS_CYRILLIC.search(text_stripped))

    await logger.info(
        "lang_detect_analysis",
        text_preview=text_stripped[:80],
        uz_latin_score=len(uz_matches),
        uz_cyrillic_score=len(uz_cyrillic_matches),
        uz_total_score=uz_score,
        ru_score=ru_score,
        uz_matches=uz_matches[:5] if uz_matches else [],
        uz_cyrillic_matches=uz_cyrillic_matches[:5] if uz_cyrillic_matches else [],
        ru_matches=ru_matches[:5] if ru_matches else [],
        has_cyrillic=has_cyrillic,
        latin_words_count=len(latin_words),
    )

    if uz_cyrillic_matches:
        await logger.info("lang_detected", lang="uz", reason="uzbek_cyrillic_markers", score=len(uz_cyrillic_matches))
        return "uz"

    if latin_words and not has_cyrillic:
        if uz_score > 0:
            await logger.info("lang_detected", lang="uz", reason="latin_with_uz_markers", score=uz_score)
            return "uz"

        if len(latin_words) >= 1:
            await logger.info("lang_detected", lang="uz", reason="latin_text_default", words=len(latin_words))
            return "uz"

    if any(c in _RU_CHARS for c in text_stripped) and ru_score >= uz_score:
        await logger.info("lang_detected", lang="ru", reason="ru_only_chars")
        return "ru"

    if uz_score > ru_score:
        await logger.info(
            "lang_detected", lang="uz", reason="uz_markers_higher",
            uz_score=uz_score, ru_score=ru_score
        )
        return "uz"
    if ru_score > uz_score:
        await logger.info(
            "lang_detected", lang="ru", reason="ru_markers_higher",
            uz_score=uz_score, ru_score=ru_score
        )
        return "ru"

    if has_cyrillic and not latin_words:
        await logger.info("lang_detected", lang="ru", reason="cyrillic_default")
        return "ru"

    await logger.info("lang_detected", lang="both", reason="ambiguous_keep_current")
    return "both"
