import json
from pathlib import Path

from src.core.logging import get_logger

logger = get_logger(__name__)

_SCRIPTS: list[dict[str, str]] = []
_SCRIPTS_TEXT: str = ""

XLSX_PATH = Path(__file__).resolve().parent.parent.parent / "response.xlsx"

def _load_with_openpyxl(path: Path) -> list[dict[str, str]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    scripts: list[dict[str, str]] = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        question = (row[0] or "").strip() if row[0] else ""
        answer = (row[1] or "").strip() if len(row) > 1 and row[1] else ""
        if question and answer:
            scripts.append({"question": question, "answer": answer})
    wb.close()
    return scripts

def load_scripts() -> list[dict[str, str]]:

    global _SCRIPTS, _SCRIPTS_TEXT
    if _SCRIPTS:
        return _SCRIPTS

    if not XLSX_PATH.exists():
        logger.warning("response_xlsx_not_found", path=str(XLSX_PATH))
        return []

    try:
        _SCRIPTS = _load_with_openpyxl(XLSX_PATH)
        _SCRIPTS_TEXT = _build_scripts_text(_SCRIPTS)
        logger.info("response_scripts_loaded", count=len(_SCRIPTS))
    except Exception as e:
        logger.error("response_scripts_load_error", error=str(e))
        _SCRIPTS = []
        _SCRIPTS_TEXT = ""

    return _SCRIPTS

def _build_scripts_text(scripts: list[dict[str, str]]) -> str:

    lines = ["═══ ГОТОВЫЕ СКРИПТЫ ОТВЕТОВ (используй эти формулировки) ═══\n"]
    for i, s in enumerate(scripts, 1):
        lines.append(f"{i}. Вопрос клиента: «{s['question']}»")
        lines.append(f"   Ответ: «{s['answer']}»\n")
    return "\n".join(lines)

def get_scripts_text() -> str:

    if not _SCRIPTS_TEXT:
        load_scripts()
    return _SCRIPTS_TEXT

def get_scripts_json() -> str:

    if not _SCRIPTS:
        load_scripts()
    return json.dumps(_SCRIPTS, ensure_ascii=False, indent=2)

def find_matching_script(query: str) -> str | None:

    if not _SCRIPTS:
        load_scripts()

    query_lower = query.lower()
    best_match: str | None = None
    best_score = 0

    for script in _SCRIPTS:
        q_words = set(script["question"].lower().split())
        overlap = sum(1 for w in q_words if w in query_lower)
        if overlap > best_score and overlap >= 2:
            best_score = overlap
            best_match = script["answer"]

    return best_match
