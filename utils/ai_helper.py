# utils/ai_helper.py
# -*- coding: utf-8 -*-
"""
Helper terpadu untuk panggilan Google Gemini (Generative Language API).

Fitur:
- Auto pilih model yang VALID via ListModels (prioritas 2.5/2.0).
- Fallback berurutan jika model 404 / tidak mendukung generateContent.
- Retry + exponential backoff untuk error sementara (429/5xx/timeout).
- Batasi panjang output (maxOutputTokens) + helper split ke chunk
  aman Telegram (≈ ≤ 3800 char) agar tidak "Message is too long".
- Penanganan error terstruktur (HTTPError detail, JSON guard, dsb).

Catatan:
- Endpoint v1beta digunakan karena paling kompatibel lintas model.
- Semua Gemini 2.x sudah multimodal; tidak perlu suffix -vision.
"""

from __future__ import annotations
import os
import time
import json
import math
import logging
from typing import List, Optional, Dict, Any

import requests
from requests import HTTPError, Response, Timeout

try:
    from config import GEMINI_API_KEY  # prefer from your config
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
API_KEY_HEADER = "x-goog-api-key"

# Prioritas model yang murah/cepat sampai powerful (per 2025)
PREFERRED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
]

# Batas aman Telegram (4096 resmi), sisakan margin untuk emoji/markdown
TELEGRAM_SAFE_LIMIT = 3800

# ---------- Util umum ----------

def _http_post(url: str, headers: Dict[str, str], payload: Dict[str, Any],
               timeout: int = 60, retries: int = 2, backoff_base: float = 0.75) -> Response:
    """
    POST dengan retry untuk error sementara: 408/429/5xx/Timeout.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=timeout)
            # Retry hanya untuk status tertentu
            if res.status_code in (408, 409, 425, 429, 500, 502, 503, 504):
                last_exc = HTTPError(f"HTTP {res.status_code}: {res.text[:600]}")
                # backoff naik
                if attempt < retries:
                    sleep_s = backoff_base * (2 ** attempt)
                    time.sleep(sleep_s)
                    continue
            res.raise_for_status()
            return res
        except Timeout as e:
            last_exc = e
            if attempt < retries:
                sleep_s = backoff_base * (2 ** attempt)
                time.sleep(sleep_s)
                continue
            raise
        except HTTPError as e:
            # Untuk 4xx selain daftar di atas, langsung lempar
            last_exc = e
            raise
        except Exception as e:
            last_exc = e
            if attempt < retries:
                sleep_s = backoff_base * (2 ** attempt)
                time.sleep(sleep_s)
                continue
            raise
    # Harusnya sudah return/raise, ini guard
    if last_exc:
        raise last_exc
    raise RuntimeError("Request gagal tanpa exception yang jelas.")

def _list_models() -> List[Dict[str, Any]]:
    """
    Ambil semua model, biar tahu mana yang support generateContent.
    """
    url = f"{API_BASE}/models"
    headers = {"Content-Type": "application/json", API_KEY_HEADER: GEMINI_API_KEY}
    res = _http_post(  # gunakan POST kosong -> beberapa gateway menolak GET tanpa key di header
        url=f"{url}?key={GEMINI_API_KEY}",
        headers=headers,
        payload={},  # body kosong aman
        timeout=30,
        retries=1
    )
    try:
        data = res.json()
    except Exception as e:
        raise RuntimeError(f"Gagal parsing ListModels JSON: {e} | raw={res.text[:400]}")

    models = data.get("models") or data.get("data") or []
    if not isinstance(models, list):
        raise RuntimeError(f"Format ListModels tidak terduga: {data}")
    return models

def _supported_models() -> List[str]:
    """
    Filter model yang mendukung generateContent, urutkan by prioritas PREFERRED_MODELS
    lalu tambahkan sisanya (mis: -flash/-pro varian minor).
    """
    models = _list_models()
    gens: List[str] = []

    def supports_generate(m: Dict[str, Any]) -> bool:
        methods = m.get("supportedGenerationMethods") or []
        if not isinstance(methods, list):
            return False
        return "generateContent" in methods

    # Normalisasi nama: biasanya "name": "models/gemini-2.5-flash"
    for m in models:
        if not supports_generate(m):
            continue
        name = m.get("name") or ""
        if name.startswith("models/"):
            name = name.split("/", 1)[1]
        if name:
            gens.append(name)

    # Urutkan: yang ada di PREFERRED_MODELS dulu
    preferred = [m for m in PREFERRED_MODELS if m in gens]
    others = [m for m in gens if m not in preferred]
    # Optional: prioritaskan yang 2.x dibanding 1.x/1.5.x
    others.sort(key=lambda s: (not s.startswith("gemini-2"), s))
    return preferred + others

def _concat_text_parts(cand: Dict[str, Any]) -> str:
    """
    Kembalikan gabungan seluruh parts (text) dari satu candidate.
    """
    content = cand.get("content") or {}
    parts = content.get("parts") or []
    texts: List[str] = []
    for p in parts:
        t = p.get("text")
        if isinstance(t, str):
            texts.append(t)
    return "".join(texts).strip()

def _call_gemini_once(model: str, prompt: str,
                      temperature: float = 0.6,
                      max_output_tokens: int = 1024) -> str:
    """
    Panggilan sekali ke model tertentu (tanpa fallback).
    """
    url = f"{API_BASE}/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", API_KEY_HEADER: GEMINI_API_KEY}
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature,
            # TopP/TopK opsional; feel free to buka jika perlu kontrol sampling:
            # "topP": 0.95,
            # "topK": 40,
            "maxOutputTokens": max_output_tokens,
            "candidateCount": 1
        }
        # safetySettings bisa ditambah jika ingin override default
    }

    res = _http_post(url=f"{url}?key={GEMINI_API_KEY}", headers=headers, payload=body, timeout=60, retries=1)
    try:
        data = res.json()
    except Exception as e:
        raise RuntimeError(f"Gagal parsing JSON: {e} | raw={res.text[:600]}")

    cands = data.get("candidates", [])
    if not cands:
        # Tidak ada kandidat; lemparkan detail response
        raise RuntimeError(f"Tidak ada kandidat balasan: {json.dumps(data)[:800]}")

    return _concat_text_parts(cands[0])

def call_gemini(prompt: str,
                preferred_models: Optional[List[str]] = None,
                temperature: float = 0.6,
                max_output_tokens: int = 1024) -> str:
    """
    Panggilan yang:
      1) Mencoba model dari daftar prioritas.
      2) Jika 404/NOT_FOUND → fallback ke model lain yang valid dari ListModels.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY tidak terdefinisi di config/env.")

    # Coba preferred dulu
    models_to_try = list(preferred_models or PREFERRED_MODELS)

    # Tambahkan model lain yang valid dari ListModels
    try:
        live = _supported_models()
        for m in live:
            if m not in models_to_try:
                models_to_try.append(m)
    except Exception as e:
        # Jika gagal list models, tetap lanjut hanya dengan preferred
        logging.warning(f"Gagal ListModels, lanjut pakai preferred: {e}")

    last_detail = None
    for model in models_to_try:
        try:
            return _call_gemini_once(model, prompt, temperature=temperature, max_output_tokens=max_output_tokens)
        except HTTPError as e:
            status = getattr(e.response, "status_code", None)
            text = getattr(e.response, "text", "")[:600] if getattr(e, "response", None) else str(e)
            last_detail = f"{model} -> HTTPError {status} | {text}"
            # 404/NOT_FOUND → lanjut coba model lain
            if status == 404:
                continue
            # Error lain: langsung lempar agar kelihatan jelas
            raise RuntimeError(f"Terjadi kesalahan pada layanan AI: {last_detail}")
        except Timeout as e:
            last_detail = f"{model} -> Timeout: {e}"
            # lanjut ke model lain, siapa tahu region berbeda lebih cepat
            continue
        except Exception as e:
            last_detail = f"{model} -> {e}"
            # lanjut ke model lain
            continue

    raise RuntimeError(f"Gagal memanggil Gemini di semua model kandidat. Detail terakhir: {last_detail}")

# ---------- Helper untuk Telegram ----------

def split_for_telegram(text: str, limit: int = TELEGRAM_SAFE_LIMIT) -> List[str]:
    """
    Pecah teks panjang menjadi potongan ≤ limit, aware code fence ``` dan batas baris.
    """
    parts: List[str] = []
    buf: List[str] = []
    size = 0
    open_code = False

    def flush():
        nonlocal buf, size, open_code
        if not buf:
            return
        chunk = "".join(buf)
        parts.append(chunk)
        buf = []
        size = 0

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        # toggle code fence
        if stripped.startswith("```"):
            open_code = not open_code

        if size + len(line) > limit:
            # tutup code fence jika sedang terbuka
            if open_code:
                buf.append("\n```")
                open_code = False
            flush()
            # kalau line sendiri > limit, hard split by chars
            if len(line) > limit:
                start = 0
                while start < len(line):
                    end = min(start + limit, len(line))
                    seg = line[start:end]
                    # jaga code fence agar tidak patah aneh (kasus langka)
                    if seg.strip().startswith("```") and not seg.strip().endswith("```"):
                        seg += "\n```"
                    parts.append(seg)
                    start = end
                continue

        buf.append(line)
        size += len(line)

    # akhir: tutup code fence jika masih terbuka
    if open_code:
        buf.append("\n```")
        open_code = False
    flush()
    return parts

# ---------- Fungsi bisnis kamu ----------

def get_professional_analysis(symbol: str,
                              timeframe: str,
                              kline_data: list,
                              funding_rate: str,
                              long_short_ratio: str,
                              *,
                              temperature: float = 0.6,
                              max_output_tokens: int = 900,
                              telegram_chunk: bool = True) -> str | List[str]:
    """
    Minta AI isi template analisa. Output:
      - default: list[str] (chunk aman Telegram) jika telegram_chunk=True
      - string utuh jika telegram_chunk=False
    """
    # ringkas OHLC biar prompt tidak meledak
    # ambil max 50 terakhir; gunakan separators kompakt untuk menghemat token
    recent_kline = kline_data[-50:]
    ohlc_json = json.dumps(recent_kline, separators=(",", ":"), ensure_ascii=False)

    prompt = f"""
Anda adalah seorang Analis Kripto Profesional. Tugas Anda adalah membuat laporan analisis ringkas dan profesional untuk pasangan {symbol}/USDT dengan timeframe {timeframe}.

Gunakan data berikut secara selektif (jangan tempel mentah-mentah):
- Candlesticks terbaru (OHLC, max 50): {ohlc_json}
- Funding Rate saat ini: {funding_rate}
- Global Long/Short Ratio: {long_short_ratio}

Wajib keluarkan dalam format Markdown dengan template berikut (isi angka spesifik, gunakan titik desimal, tanpa menambah seksi baru). JANGAN menyalin ulang seluruh OHLC.

--- TEMPLATE LAPORAN ---
📈 **Hasil Analisa Lengkap untuk {symbol}/USDT ({timeframe})**

* **Entry Price:** $[harga_entry]
* **Stop Loss:** $[harga_sl]
* **Take Profit 1:** $[harga_tp1]
* **Take Profit 2:** $[harga_tp2]
* **Take Profit 3:** $[harga_tp3]

---
📊 **Ringkasan Analisis**

* **Analisa Candle & Chart Pattern:** [Pola utama & level penting].
* **Analisa Data Pasar:** [Interpretasi Funding Rate & Long/Short Ratio].
--- BATAS OUTPUT: maksimum ~3200 karakter, tidak perlu penjelasan bertele-tele.
""".strip()

    try:
        text = call_gemini(
            prompt=prompt,
            preferred_models=PREFERRED_MODELS,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    except Exception as e:
        # Seragamkan pesan error supaya mudah dilacak di bot
        return f"Terjadi kesalahan pada layanan AI: {e}"

    if telegram_chunk:
        return split_for_telegram(text, TELEGRAM_SAFE_LIMIT)
    return text
