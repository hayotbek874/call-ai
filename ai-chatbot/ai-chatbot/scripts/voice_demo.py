#!/usr/bin/env python3
"""
Full-featured voice demo with CRM tools, response scripts, and function calling.

TWO modes in ONE process:
  1. Web UI      (port 8080) — open in browser, click mic, talk, hear reply
  2. AudioSocket (port 9099) — Asterisk connects here for real phone calls

Features:
  - Real ZargarShop system prompt (same as production)
  - CRM integration: search products, get details, stock, categories, orders
  - OpenAI function-calling loop (up to 5 rounds per turn)
  - Response scripts from response.xlsx
  - Multi-turn conversation history

Usage:
  python scripts/voice_demo.py

Then open http://localhost:8080 (or http://<server-ip>:8080)

Env vars required (from .env):
  OPENAI_API_KEY, CRM_BASE_URL, CRM_API_KEY, REDIS_URL
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import struct
import sys
import time
import wave
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import openai
import redis.asyncio as aioredis

from src.core.logging import setup_logging
setup_logging()

from src.clients.crm_client import CRMClient
from src.services.ai.crm_service import CRMService
from src.services.ai.tools import TOOLS, ToolExecutor
from src.services.ai.prompt_builder import build_system_prompt
from src.utils.response_scripts import load_scripts

# ── Config ──────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
STT_MODEL = os.getenv("OPENAI_STT_MODEL", "whisper-1")
TTS_VOICE_RU = os.getenv("OPENAI_TTS_VOICE_RU", "nova")
TTS_VOICE_UZ = os.getenv("OPENAI_TTS_VOICE_UZ", "nova")
WEB_PORT = int(os.getenv("VOICE_DEMO_WEB_PORT", "8080"))
AUDIOSOCKET_PORT = int(os.getenv("AUDIOSOCKET_PORT", "9099"))
SILENCE_THRESHOLD = 500
SILENCE_FRAMES_END = 35
FRAME_SIZE = 320
MAX_TOOL_ROUNDS = 5

# Uzbek keywords for language detection
UZ_KEYWORDS = {
    "salom", "rahmat", "kerak", "qancha", "narxi", "bor", "yoq", "ha", "yoʻq",
    "men", "siz", "bu", "nima", "qaysi", "uchun", "qiling", "berish", "olish",
    "mahsulot", "buyurtma", "yetkazib", "manzil", "telefon", "chegirma",
    "kumush", "uzuk", "taqinchoq", "sovg'a", "iltimos", "xayr", "assalomu",
    "alaykum", "va'alaykum", "qalay", "yaxshi", "yomon", "nega", "qachon",
    "qanday", "kimga", "nimaga", "qayerda", "katta", "kichik", "yangi",
}

# AudioSocket protocol
FRAME_HANGUP = 0x00
FRAME_UUID = 0x01
FRAME_AUDIO = 0x10

# ── Global clients (initialized in main) ────────────────────────────
ai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
redis_client: aioredis.Redis | None = None
crm_service: CRMService | None = None
tool_executor: ToolExecutor | None = None


# ════════════════════════════════════════════════════════════════════
#  LOGGING HELPERS
# ════════════════════════════════════════════════════════════════════

def log(level: str, component: str, action: str, **kwargs) -> None:
    """Structured logging with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    details = " ".join(f"{k}={repr(v)[:100]}" for k, v in kwargs.items())
    emoji = {"INFO": "ℹ️", "DEBUG": "🔍", "WARN": "⚠️", "ERROR": "❌", "OK": "✅"}.get(level, "•")
    print(f"[{ts}] {emoji} [{component}] {action} {details}")


def log_request(component: str, func_name: str, **params) -> float:
    """Log incoming request, return start time for duration calc."""
    log("INFO", component, f"{func_name} REQUEST", **params)
    return time.time()


def log_response(component: str, func_name: str, start: float, **result) -> None:
    """Log response with duration."""
    duration_ms = int((time.time() - start) * 1000)
    log("OK", component, f"{func_name} RESPONSE", duration_ms=duration_ms, **result)


def log_error(component: str, func_name: str, error: Exception) -> None:
    """Log error."""
    log("ERROR", component, f"{func_name} FAILED", error=str(error))


def _build_system_prompt(lang: str) -> str:
    """Build the full production system prompt with scripts."""
    return build_system_prompt(language=lang, summary=None, product_context=None)


def detect_language(text: str) -> str:
    """Detect language from text using keyword matching. Returns 'ru' or 'uz'."""
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    uz_matches = words & UZ_KEYWORDS
    # Also check for Cyrillic vs Latin
    cyrillic_count = len(re.findall(r'[а-яёА-ЯЁ]', text))
    latin_count = len(re.findall(r"[a-zA-Z'`]", text))
    
    if uz_matches or latin_count > cyrillic_count:
        log("DEBUG", "LANG", "detected", result="uz", uz_keywords=list(uz_matches)[:5], latin=latin_count, cyrillic=cyrillic_count)
        return "uz"
    log("DEBUG", "LANG", "detected", result="ru", cyrillic=cyrillic_count, latin=latin_count)
    return "ru"


def get_voice_for_lang(lang: str) -> str:
    """Get TTS voice for language."""
    return TTS_VOICE_UZ if lang == "uz" else TTS_VOICE_RU


# ════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ════════════════════════════════════════════════════════════════════

def rms(pcm: bytes) -> int:
    if len(pcm) < 2:
        return 0
    n = len(pcm) // 2
    samples = struct.unpack(f"<{n}h", pcm[: n * 2])
    return int((sum(s * s for s in samples) / n) ** 0.5)


def pcm_to_wav(pcm: bytes, rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def resample_24k_to_8k(pcm_24k: bytes) -> bytes:
    n = len(pcm_24k) // 2
    if n < 3:
        return b""
    samples = struct.unpack(f"<{n}h", pcm_24k)
    out = []
    for i in range(0, n - 2, 3):
        avg = (samples[i] + samples[i + 1] + samples[i + 2]) // 3
        out.append(max(-32768, min(32767, avg)))
    return struct.pack(f"<{len(out)}h", *out)


async def stt(audio_bytes: bytes, fmt: str = "wav", detect_lang: bool = False) -> tuple[str, str | None]:
    """Speech-to-text. Returns (text, detected_language) if detect_lang=True."""
    start = log_request("STT", "transcribe", format=fmt, audio_bytes=len(audio_bytes))
    
    ext = fmt if fmt in ("wav", "webm", "mp3", "ogg") else "webm"
    mime = {
        "wav": "audio/wav", "webm": "audio/webm",
        "mp3": "audio/mp3", "ogg": "audio/ogg",
    }.get(ext, "audio/webm")
    
    try:
        # Don't force language to allow detection
        result = await ai_client.audio.transcriptions.create(
            model=STT_MODEL,
            file=(f"audio.{ext}", io.BytesIO(audio_bytes), mime),
        )
        text = result.text.strip()
        
        # Detect language from transcribed text
        detected = None
        if detect_lang and text:
            detected = detect_language(text)
        
        log_response("STT", "transcribe", start, text_len=len(text), text_preview=text[:60], detected_lang=detected)
        return text, detected
    except Exception as e:
        log_error("STT", "transcribe", e)
        raise


async def chat_with_tools(history: list[dict], user_text: str) -> str:
    """Full function-calling loop: user text → (tool calls) → final answer."""
    start = log_request("AI", "chat_with_tools", user_text=user_text[:80], history_len=len(history))
    history.append({"role": "user", "content": user_text})

    tools_called = []
    for round_num in range(MAX_TOOL_ROUNDS):
        log("DEBUG", "AI", f"round {round_num + 1}/{MAX_TOOL_ROUNDS}", has_tools=bool(tool_executor))
        
        kwargs: dict = {
            "model": "gpt-4o",
            "messages": history,
            "max_tokens": 300,
            "temperature": 0.7,
        }
        # Only offer tools if we have CRM (and not on last round)
        if tool_executor and round_num < MAX_TOOL_ROUNDS - 1:
            kwargs["tools"] = TOOLS
            kwargs["tool_choice"] = "auto"
            log("DEBUG", "AI", "tools_offered", tools_count=len(TOOLS))

        api_start = time.time()
        resp = await ai_client.chat.completions.create(**kwargs)
        api_ms = int((time.time() - api_start) * 1000)
        msg = resp.choices[0].message
        
        log("DEBUG", "AI", "openai_response", duration_ms=api_ms, has_tool_calls=bool(msg.tool_calls), finish_reason=resp.choices[0].finish_reason)

        # If the model wants to call tools
        if msg.tool_calls and tool_executor:
            # Append assistant message with tool_calls
            history.append(msg.model_dump(exclude_none=True))

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                tool_start = log_request("TOOL", fn_name, **fn_args)
                try:
                    result = await tool_executor.execute(fn_name, fn_args)
                    log_response("TOOL", fn_name, tool_start, result_len=len(result), result_preview=result[:150])
                    tools_called.append(fn_name)
                except Exception as e:
                    log_error("TOOL", fn_name, e)
                    result = f"Error: {e}"

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            # Continue loop — model will process tool results
            continue

        # No tool calls — we have the final answer
        answer = msg.content or ""
        history.append({"role": "assistant", "content": answer})
        break
    else:
        # Exhausted rounds — force a text reply
        log("WARN", "AI", "max_rounds_exhausted")
        resp = await ai_client.chat.completions.create(
            model="gpt-4o", messages=history, max_tokens=300, temperature=0.7,
        )
        answer = resp.choices[0].message.content or ""
        history.append({"role": "assistant", "content": answer})

    # Trim history to avoid token overflow
    if len(history) > 40:
        history[:] = history[:1] + history[-30:]
    
    log_response("AI", "chat_with_tools", start, answer_len=len(answer), answer_preview=answer[:100], tools_called=tools_called)
    return answer


async def tts_mp3(text: str, voice: str | None = None) -> bytes:
    """Generate TTS as complete MP3 bytes (for web UI)."""
    voice = voice or TTS_VOICE_RU
    start = log_request("TTS", "generate_mp3", text_len=len(text), text_preview=text[:60], voice=voice)
    
    try:
        response = await ai_client.audio.speech.create(
            model=TTS_MODEL, voice=voice, input=text, response_format="mp3",
        )
        chunks = []
        stream = response.aiter_bytes(chunk_size=8192)
        if hasattr(stream, "__await__"):
            stream = await stream
        async for chunk in stream:
            chunks.append(chunk)
        audio = b"".join(chunks)
        log_response("TTS", "generate_mp3", start, audio_bytes=len(audio))
        return audio
    except Exception as e:
        log_error("TTS", "generate_mp3", e)
        raise


# ════════════════════════════════════════════════════════════════════
#  WEB UI HTML
# ════════════════════════════════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZargarShop Voice Demo</title>
<style>
:root{--bg:#0f1117;--sf:#1a1d27;--sf2:#242836;--bd:#2e3345;--pr:#6c5ce7;--pl:#a29bfe;--ac:#00cec9;--tx:#e4e6ef;--mt:#8b8fa3;--dn:#ff6b6b;--ok:#51cf66}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;display:flex;flex-direction:column;align-items:center}
.hd{width:100%;padding:18px 24px;background:var(--sf);border-bottom:1px solid var(--bd);text-align:center}
.hd h1{font-size:22px;font-weight:700;background:linear-gradient(135deg,var(--pl),var(--ac));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hd p{font-size:12px;color:var(--mt);margin-top:4px}
.wrap{flex:1;width:100%;max-width:480px;display:flex;flex-direction:column;padding:20px;gap:16px}
.msgs{flex:1;overflow-y:auto;display:flex;flex-direction:column;gap:10px;min-height:240px;max-height:50vh;padding:8px 0;scroll-behavior:smooth}
.msg{padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.5;max-width:82%;word-wrap:break-word;animation:fadeIn .25s ease}
.msg.u{background:var(--pr);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
.msg.b{background:var(--sf);border:1px solid var(--bd);align-self:flex-start;border-bottom-left-radius:4px}
.msg.s{align-self:center;color:var(--mt);font-size:12px;background:none;padding:4px}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.bar{display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px solid var(--bd)}
.mic{width:72px;height:72px;border-radius:50%;border:2px solid var(--bd);background:var(--sf);color:var(--pl);font-size:30px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;flex-shrink:0;user-select:none;-webkit-user-select:none;-webkit-tap-highlight-color:transparent}
.mic:hover{border-color:var(--pl);background:var(--sf2)}
.mic.rec{background:var(--dn);color:#fff;border-color:var(--dn);transform:scale(1.08);animation:pulse 1s infinite}
.mic.wait{background:var(--sf);color:var(--mt);border-color:var(--bd);pointer-events:none;opacity:.5}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(255,107,107,.4)}50%{box-shadow:0 0 0 14px transparent}}
.stx{flex:1;font-size:14px;color:var(--mt);text-align:center}
.lang{display:flex;gap:8px;justify-content:center}
.lang button{padding:6px 16px;border-radius:18px;border:1px solid var(--bd);background:var(--sf);color:var(--mt);cursor:pointer;font-size:13px;transition:all .15s;font-family:inherit}
.lang button.on{background:var(--pr);color:#fff;border-color:var(--pr)}
.lang button:hover{border-color:var(--pl)}
.prog{width:100%;height:4px;border-radius:2px;background:var(--bd);overflow:hidden}
.prog .fill{height:100%;width:0;background:linear-gradient(90deg,var(--pr),var(--ac));transition:width .3s ease}
.tip{text-align:center;font-size:11px;color:var(--mt);margin-top:-8px}
</style>
</head>
<body>

<div class="hd">
  <h1>💎 ZargarShop Voice Demo</h1>
  <p>AI голосовой ассистент — нажмите и говорите</p>
</div>

<div class="wrap">
  <div class="lang">
    <button class="on" data-l="ru">🇷🇺 Русский</button>
    <button data-l="uz">🇺🇿 O'zbek</button>
  </div>

  <div class="msgs" id="msgs"></div>

  <div class="prog"><div class="fill" id="prog"></div></div>

  <div class="bar">
    <button class="mic" id="mic" title="Hold to speak">🎤</button>
    <div class="stx" id="stx">Удерживайте 🎤 и говорите</div>
  </div>
  <div class="tip">💡 Hold the microphone button while speaking, release when done</div>
</div>

<script>
const API = location.origin;
let lang = 'ru';
let history = [];
let rec = null, stream = null, chunks = [];
let busy = false;
const mic = document.getElementById('mic');
const stx = document.getElementById('stx');
const msgs = document.getElementById('msgs');
const prog = document.getElementById('prog');

// ── Lang toggle
document.querySelectorAll('.lang button').forEach(b => {
  b.onclick = () => {
    if (busy) return;
    document.querySelectorAll('.lang button').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    lang = b.dataset.l;
    history = [];
    addMsg('s', lang === 'ru' ? '🔄 Язык: Русский' : "🔄 Til: O'zbek");
    stx.textContent = lang === 'ru' ? 'Удерживайте 🎤 и говорите' : "🎤 ni bosib gapiring";
  };
});

// ── Mic — hold to record
function startRec(e) {
  e.preventDefault();
  if (busy) return;
  navigator.mediaDevices.getUserMedia({audio: {echoCancellation:true, noiseSuppression:true}}).then(s => {
    stream = s;
    chunks = [];
    rec = new MediaRecorder(s, {mimeType: 'audio/webm;codecs=opus'});
    rec.ondataavailable = ev => { if (ev.data.size > 0) chunks.push(ev.data); };
    rec.onstop = onRecStop;
    rec.start();
    mic.classList.add('rec');
    stx.textContent = lang === 'ru' ? '🎙️ Говорите...' : '🎙️ Gapiring...';
  }).catch(() => {
    stx.textContent = '❌ Microphone access denied';
  });
}

function stopRec(e) {
  e.preventDefault();
  if (rec && rec.state === 'recording') {
    rec.stop();
    if (stream) stream.getTracks().forEach(t => t.stop());
  }
  mic.classList.remove('rec');
}

mic.addEventListener('mousedown', startRec);
mic.addEventListener('touchstart', startRec, {passive: false});
mic.addEventListener('mouseup', stopRec);
mic.addEventListener('touchend', stopRec, {passive: false});
mic.addEventListener('mouseleave', stopRec);

async function onRecStop() {
  if (chunks.length === 0) return;
  const blob = new Blob(chunks, {type: 'audio/webm'});
  if (blob.size < 500) { stx.textContent = 'Too short — hold longer'; return; }

  busy = true;
  mic.classList.add('wait');
  stx.textContent = lang === 'ru' ? '🤔 Обработка...' : '🤔 Qayta ishlanmoqda...';
  prog.style.width = '25%';

  try {
    const form = new FormData();
    form.append('audio', blob, 'audio.webm');
    form.append('lang', lang);
    form.append('history', JSON.stringify(history));

    prog.style.width = '40%';
    const resp = await fetch(API + '/api/voice', {method: 'POST', body: form});
    if (!resp.ok) throw new Error('Server error ' + resp.status);

    const data = await resp.json();
    prog.style.width = '70%';

    if (data.error) { addMsg('s', '⚠️ ' + data.error); done(); return; }
    if (data.transcript) addMsg('u', data.transcript);
    if (data.response) addMsg('b', data.response);
    history = data.history || history;

    if (data.audio_b64) {
      stx.textContent = '🔊 ' + (lang === 'ru' ? 'Отвечаю...' : 'Javob bermoqdaman...');
      prog.style.width = '85%';
      const raw = Uint8Array.from(atob(data.audio_b64), c => c.charCodeAt(0));
      const audioBlob = new Blob([raw], {type: 'audio/mp3'});
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      audio.onended = () => { URL.revokeObjectURL(url); done(); };
      audio.onerror = () => done();
      await audio.play();
    } else { done(); }
  } catch (err) {
    addMsg('s', '⚠️ ' + err.message);
    done();
  }
}

function done() {
  busy = false;
  mic.classList.remove('wait');
  stx.textContent = lang === 'ru' ? 'Удерживайте 🎤 и говорите' : "🎤 ni bosib gapiring";
  prog.style.width = '0';
}

function addMsg(type, text) {
  const d = document.createElement('div');
  d.className = 'msg ' + type;
  d.textContent = text;
  msgs.appendChild(d);
  msgs.scrollTop = msgs.scrollHeight;
}

addMsg('s', '💎 Добро пожаловать! Удерживайте микрофон и говорите.');
</script>
</body>
</html>"""


# ════════════════════════════════════════════════════════════════════
#  WEB SERVER (pure asyncio — no aiohttp/fastapi needed)
# ════════════════════════════════════════════════════════════════════

async def handle_http(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Minimal HTTP server: serves HTML page + POST /api/voice endpoint."""
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not request_line:
            writer.close(); return

        parts = request_line.decode(errors="replace").split()
        if len(parts) < 2:
            writer.close(); return
        method, path = parts[0], parts[1]

        # Read headers
        headers: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if line in (b"\r\n", b"\n", b""):
                break
            if b":" in line:
                k, v = line.decode(errors="replace").split(":", 1)
                headers[k.strip().lower()] = v.strip()
        content_length = int(headers.get("content-length", 0))

        # ── GET / → HTML page
        if method == "GET" and path in ("/", "/index.html"):
            body = HTML_PAGE.encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            await writer.drain()

        # ── POST /api/voice → process audio
        elif method == "POST" and path == "/api/voice":
            body = await asyncio.wait_for(
                reader.readexactly(content_length), timeout=30,
            )
            result = await _process_voice(body, headers)
            resp_body = json.dumps(result, ensure_ascii=False).encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Content-Length: " + str(len(resp_body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + resp_body
            )
            await writer.drain()

        # ── CORS preflight
        elif method == "OPTIONS":
            writer.write(
                b"HTTP/1.1 204 No Content\r\n"
                b"Access-Control-Allow-Origin: *\r\n"
                b"Access-Control-Allow-Methods: POST, GET, OPTIONS\r\n"
                b"Access-Control-Allow-Headers: *\r\n"
                b"Connection: close\r\n\r\n"
            )
            await writer.drain()

        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
            await writer.drain()

    except Exception as e:
        print(f"  [HTTP] Error: {e}")
        try:
            writer.write(b"HTTP/1.1 500 Error\r\nConnection: close\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


def _parse_multipart(body: bytes, boundary: bytes) -> dict[str, tuple[str, bytes]]:
    """Minimal multipart/form-data parser."""
    parts = body.split(b"--" + boundary)
    result: dict[str, tuple[str, bytes]] = {}
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        hdr_end = part.find(b"\r\n\r\n")
        if hdr_end < 0:
            continue
        hdr = part[:hdr_end].decode(errors="replace")
        data = part[hdr_end + 4 :]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        m_name = re.search(r'name="([^"]*)"', hdr)
        m_file = re.search(r'filename="([^"]*)"', hdr)
        if m_name:
            result[m_name.group(1)] = (m_file.group(1) if m_file else "", data)
    return result


async def _process_voice(body: bytes, headers: dict) -> dict:
    """POST /api/voice handler: audio → STT → AI → TTS → JSON."""
    ct = headers.get("content-type", "")
    if "boundary=" not in ct:
        return {"error": "Expected multipart/form-data"}

    boundary = ct.split("boundary=")[1].strip().encode()
    fields = _parse_multipart(body, boundary)

    _, audio_data = fields.get("audio", ("", b""))
    _, lang_raw = fields.get("lang", ("", b"ru"))
    _, hist_raw = fields.get("history", ("", b"[]"))

    lang = lang_raw.decode(errors="replace").strip() or "ru"
    try:
        history = json.loads(hist_raw.decode(errors="replace"))
    except Exception:
        history = []

    if not history or history[0].get("role") != "system":
        sys_prompt = _build_system_prompt(lang)
        history.insert(0, {"role": "system", "content": sys_prompt})

    if len(audio_data) < 100:
        return {"error": "Audio too small"}

    print(f"  [WEB] 🎤 {len(audio_data)} bytes audio received")

    # STT
    try:
        fmt = "webm"
        if audio_data[:4] == b"RIFF":
            fmt = "wav"
        elif audio_data[:3] == b"ID3" or audio_data[:2] == b"\xff\xfb":
            fmt = "mp3"
        transcript = await stt(audio_data, fmt)
    except Exception as e:
        print(f"  [WEB] ❌ STT error: {e}")
        return {"error": f"STT failed: {e}"}

    if not transcript:
        return {"transcript": "", "response": "", "history": history}

    print(f"  [WEB] 📝 {transcript}")

    # AI with function-calling tools
    try:
        response = await chat_with_tools(history, transcript)
    except Exception as e:
        print(f"  [WEB] ❌ AI error: {e}")
        response = "Извините, ошибка. Повторите."

    print(f"  [WEB] 🤖 {response}")

    # TTS
    audio_b64 = ""
    try:
        mp3 = await tts_mp3(response)
        audio_b64 = base64.b64encode(mp3).decode()
        print(f"  [WEB] 🔊 {len(mp3)} bytes MP3")
    except Exception as e:
        print(f"  [WEB] ❌ TTS error: {e}")

    return {
        "transcript": transcript,
        "response": response,
        "audio_b64": audio_b64,
        "history": history,
    }


# ════════════════════════════════════════════════════════════════════
#  AUDIOSOCKET SERVER (for real Asterisk phone calls)
# ════════════════════════════════════════════════════════════════════

def _build_audio_frame(pcm: bytes) -> bytes:
    return bytes([FRAME_AUDIO]) + len(pcm).to_bytes(2, "big") + pcm


async def _read_as_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    header = await reader.readexactly(3)
    ftype = header[0]
    length = int.from_bytes(header[1:3], "big")
    payload = await reader.readexactly(length) if length else b""
    return ftype, payload


async def _say_asterisk(writer: asyncio.StreamWriter, text: str, voice: str | None = None) -> None:
    """TTS → resample 24k→8k → AudioSocket frames."""
    voice = voice or TTS_VOICE_RU
    start = log_request("TTS", "speak_asterisk", text_len=len(text), text_preview=text[:60], voice=voice)
    
    try:
        response = await ai_client.audio.speech.create(
            model=TTS_MODEL, voice=voice, input=text, response_format="pcm",
        )
        total_bytes = 0
        stream = response.aiter_bytes(chunk_size=4800)
        if hasattr(stream, "__await__"):
            stream = await stream
        async for chunk_24k in stream:
            pcm_8k = resample_24k_to_8k(chunk_24k)
            total_bytes += len(pcm_8k)
            offset = 0
            while offset < len(pcm_8k):
                c = pcm_8k[offset : offset + FRAME_SIZE]
                if len(c) < FRAME_SIZE:
                    c += b"\x00" * (FRAME_SIZE - len(c))
                writer.write(_build_audio_frame(c))
                await writer.drain()
                offset += FRAME_SIZE
                await asyncio.sleep(0.018)
        log_response("TTS", "speak_asterisk", start, audio_bytes=total_bytes)
    except Exception as e:
        log_error("TTS", "speak_asterisk", e)
        raise


async def handle_asterisk(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle one AudioSocket TCP connection from Asterisk."""
    call_start = time.time()
    peer = writer.get_extra_info("peername")
    
    log("INFO", "CALL", "new_connection", peer=peer)
    print(f"\n{'═' * 70}")
    print(f"  📞 NEW CALL from {peer}")
    print(f"{'═' * 70}")

    try:
        ftype, payload = await asyncio.wait_for(_read_as_frame(reader), timeout=5)
    except Exception as e:
        log_error("CALL", "uuid_read", e)
        writer.close(); return

    if ftype != FRAME_UUID:
        log("ERROR", "CALL", "bad_first_frame", ftype=hex(ftype))
        writer.close(); return

    phone = payload.hex()[20:].lstrip("0") or "unknown" if len(payload) == 16 else "unknown"
    log("INFO", "CALL", "caller_identified", phone=phone)

    # Start with Russian, will switch based on user's language
    current_lang = "ru"
    current_voice = TTS_VOICE_RU
    sys_prompt = _build_system_prompt(current_lang)
    history: list[dict] = [{"role": "system", "content": sys_prompt}]

    # ═══ BILINGUAL GREETING ═══
    greeting_ru = "Здравствуйте! Я голосовой ассистент ЗаргарШоп."
    greeting_uz = "Assalomu alaykum! Men ZargarShop ovozli yordamchisiman."
    greeting_both = f"{greeting_ru} ... {greeting_uz} ... Слушаю вас. Sizni tinglayman."
    
    try:
        log("INFO", "CALL", "playing_bilingual_greeting")
        await _say_asterisk(writer, greeting_both, TTS_VOICE_RU)
        log("OK", "CALL", "greeting_played")
    except Exception as e:
        log_error("CALL", "greeting", e)
        writer.close(); return

    # Listen → STT → AI → TTS loop
    buffer = bytearray()
    speaking = False
    silence_count = 0
    turn = 0
    language_detected = False

    try:
        while True:
            ftype, payload = await _read_as_frame(reader)
            if ftype == FRAME_HANGUP:
                log("INFO", "CALL", "hangup_received")
                break
            if ftype != FRAME_AUDIO:
                continue

            if rms(payload) > SILENCE_THRESHOLD:
                speaking = True
                silence_count = 0
                buffer.extend(payload)
            elif speaking:
                silence_count += 1
                buffer.extend(payload)
                if silence_count >= SILENCE_FRAMES_END:
                    turn += 1
                    audio = bytes(buffer)
                    buffer.clear()
                    speaking = False
                    silence_count = 0

                    print(f"\n  ─── Turn {turn} {'─' * 50}")
                    log("INFO", "CALL", f"turn_{turn}_start", audio_bytes=len(audio))
                    
                    wav = pcm_to_wav(audio)
                    try:
                        # Detect language on first turn
                        text, detected_lang = await stt(wav, "wav", detect_lang=not language_detected)
                    except Exception as e:
                        log_error("CALL", f"turn_{turn}_stt", e)
                        continue
                    
                    if not text:
                        log("WARN", "CALL", f"turn_{turn}_empty_stt")
                        continue
                    
                    # Switch language if detected differently on first turn
                    if not language_detected and detected_lang:
                        language_detected = True
                        if detected_lang != current_lang:
                            current_lang = detected_lang
                            current_voice = get_voice_for_lang(current_lang)
                            # Rebuild system prompt for new language
                            sys_prompt = _build_system_prompt(current_lang)
                            history[0] = {"role": "system", "content": sys_prompt}
                            log("INFO", "CALL", "language_switched", new_lang=current_lang, new_voice=current_voice)
                            print(f"  🌐 Language switched to: {current_lang.upper()}")
                    
                    print(f"  📝 USER: {text}")
                    
                    try:
                        resp = await chat_with_tools(history, text)
                        
                        # Auto-detect language in response and adjust if needed
                        resp_lang = detect_language(resp)
                        if resp_lang != current_lang:
                            log("DEBUG", "CALL", "response_lang_mismatch", expected=current_lang, got=resp_lang)
                        
                    except Exception as e:
                        log_error("CALL", f"turn_{turn}_ai", e)
                        resp = "Извините, произошла ошибка. Iltimos, kechiring." if current_lang == "uz" else "Извините, ошибка."
                    
                    print(f"  🤖 BOT: {resp}")
                    
                    await _say_asterisk(writer, resp, current_voice)
                    log("OK", "CALL", f"turn_{turn}_complete", lang=current_lang)

    except (EOFError, ConnectionResetError, asyncio.IncompleteReadError) as e:
        log("INFO", "CALL", "disconnected", reason=type(e).__name__)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        call_duration = int(time.time() - call_start)
        log("INFO", "CALL", "ended", phone=phone, turns=turn, duration_sec=call_duration, final_lang=current_lang)
        print(f"{'═' * 70}")
        print(f"  📞 CALL ENDED: {turn} turns, {call_duration}s, lang={current_lang}")
        print(f"{'═' * 70}\n")


# ════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════

async def main():
    global redis_client, crm_service, tool_executor

    # ── Initialize CRM + Redis ──────────────────────────────────────
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    crm_url = os.getenv("CRM_BASE_URL", "")
    crm_key = os.getenv("CRM_API_KEY", "")

    crm_ok = False
    if crm_url and crm_key:
        try:
            redis_client = aioredis.from_url(redis_url)
            await redis_client.ping()
            crm = CRMClient(crm_url=crm_url, api_key=crm_key)
            crm_service = CRMService(crm, redis_client)
            tool_executor = ToolExecutor(crm_service)
            crm_ok = True
            print("✅ CRM + Redis connected — tools enabled")
        except Exception as e:
            print(f"⚠️  CRM/Redis init failed: {e} — running without tools")
            tool_executor = None
    else:
        print("⚠️  CRM_BASE_URL or CRM_API_KEY not set — running without CRM tools")

    # ── Load response scripts ───────────────────────────────────────
    try:
        scripts = load_scripts()
        print(f"✅ Loaded {len(scripts)} response scripts from response.xlsx")
    except Exception as e:
        print(f"⚠️  Could not load response scripts: {e}")

    # ── Start servers ───────────────────────────────────────────────
    web_srv = await asyncio.start_server(handle_http, "0.0.0.0", WEB_PORT)
    as_srv = await asyncio.start_server(handle_asterisk, "0.0.0.0", AUDIOSOCKET_PORT)

    tools_status = f"{'✅ ' + str(len(TOOLS)) + ' tools':20}" if crm_ok else "❌ disabled (no CRM) "

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         🎙️  VOICE DEMO — Full Featured                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🌐 Web UI:       http://localhost:{WEB_PORT:<27}║
║  📞 AudioSocket:  0.0.0.0:{AUDIOSOCKET_PORT:<33}║
║                                                              ║
║  TTS: {TTS_MODEL:<16} Voice: {TTS_VOICE:<23}║
║  STT: {STT_MODEL:<16} AI: gpt-4o + tools            ║
║  CRM tools:       {tools_status}║
║                                                              ║
║  Features:                                                   ║
║    • Real ZargarShop system prompt                           ║
║    • CRM: search, details, stock, categories, orders         ║
║    • Function-calling loop (up to {MAX_TOOL_ROUNDS} rounds)                ║
║    • Response scripts from response.xlsx                     ║
║                                                              ║
║  Ctrl+C to stop                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

    try:
        await asyncio.gather(
            web_srv.serve_forever(),
            as_srv.serve_forever(),
        )
    finally:
        if redis_client:
            await redis_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped")
