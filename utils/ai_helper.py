# utils/ai_helper.py

import requests
import json
from config import GEMINI_API_KEY

def get_professional_analysis(symbol: str, timeframe: str, kline_data: list, funding_rate: str, long_short_ratio: str):
    """
    Meminta AI untuk mengisi template laporan analisis profesional (HANYA TEKS).
    """
    recent_kline = kline_data[-50:]

    # ===== PROMPT YANG DISEMPURNAKAN (VERSI 2) DIMULAI DI SINI =====
    prompt = f"""
    Anda adalah seorang Analis Kripto Profesional dan Trader Ahli.
    Gaya bahasa Anda lugas, percaya diri, dan langsung ke intinya. Tugas Anda adalah memberikan analisis teknikal yang tajam dan actionable untuk pasangan {symbol}/USDT dengan timeframe {timeframe}.

    **Instruksi Penting:**
    1.  Isi template laporan di bawah ini dengan analisis Anda dalam format Markdown.
    2.  Berikan angka yang **spesifik, jelas, dan realistis** untuk setiap level harga.
    3.  Gunakan format `$[harga]` untuk semua harga (contoh: `$65,123.45`).
    4.  **JANGAN PERNAH** mengubah struktur atau format dari template laporan ini.
    5.  Tentukan apakah sinyal cenderung 'Long' atau 'Short' berdasarkan analisis Anda.

    --- TEMPLATE LAPORAN ---
    📊 Analisis Profesional: {symbol}/USDT ({timeframe})

    Rekomendasi Sinyal: `[Tulis Long atau Short di sini]`

    ---
    🎯 Target Entry:
    • Entry Price: `$[harga_entry]`

    🛡️ Manajemen Risiko:
    • Stop Loss: `$[harga_sl]`

    💰 Target Keuntungan (Take Profit):
    • TP 1: `$[harga_tp1]`
    • TP 2: `$[harga_tp2]`
    • TP 3: `$[harga_tp3]`

    ---
    📝 Ringkasan Analisis

    🕯️ Analisa Candle & Chart Pattern:
    [Berikan analisis ringkas dan padat di sini. Sebutkan pola candlestick atau chart pattern utama yang teridentifikasi (misal: Bullish Engulfing, Head and Shoulders, Rising Wedge) dan apa implikasinya.]

    📈 Analisa Data Pasar (Sentimen):
    [Berikan analisis singkat mengenai sentimen pasar berdasarkan Funding Rate dan Long/Short Ratio. Contoh: "Funding rate positif menandakan sentimen bullish, namun rasio long/short yang ekstrem menunjukkan potensi likuidasi.".]
    """
    # ===== PROMPT YANG DISEMPURNAKAN SELESAI =====

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.6}}

    try:
        res = requests.post(url, headers=headers, json=body, timeout=60)
        res.raise_for_status()
        raw_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Membersihkan spasi yang mungkin ada di antara $ dan angka
        raw_text = raw_text.replace('$ ', '$')
        # Mengganti format agar harga berada di dalam code block
        formatted_text = raw_text.replace('`$', '`$').replace('$', '`$')
        return formatted_text

    except Exception as e:
        print(f"Error saat menghubungi Gemini API: {e}")
        return f"Terjadi kesalahan pada layanan AI: {e}"