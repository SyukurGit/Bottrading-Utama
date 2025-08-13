# utils/ai_helper.py

import requests
import json
from config import GEMINI_API_KEY

def get_professional_analysis(symbol: str, timeframe: str, kline_data: list, funding_rate: str, long_short_ratio: str):
    """
    Meminta AI untuk mengisi template laporan analisis profesional (HANYA TEKS).
    """
    recent_kline = kline_data[-50:]

    prompt = f"""
    Anda adalah seorang Analis Kripto Profesional. Tugas Anda adalah membuat laporan analisis yang ringkas dan profesional untuk pasangan {symbol}/USDT dengan timeframe {timeframe}.

    Gunakan data di bawah ini:
    - Data Candlestick (OHLC): {json.dumps(recent_kline)}
    - Funding Rate Saat Ini: {funding_rate}
    - Global Long/Short Ratio: {long_short_ratio}

    Isi template laporan di bawah ini dengan analisis Anda dalam format Markdown. Berikan angka yang spesifik dan jelas untuk setiap level harga. JANGAN mengubah format template.

    --- TEMPLATE LAPORAN ---
    📈 **Hasil Analisa Lengkap untuk {symbol}/USDT ({timeframe})**

    * **Entry Price:** $[harga_entry]
    * **Stop Loss:** $[harga_sl]
    * **Take Profit 1:** $[harga_tp1]
    * **Take Profit 2:** $[harga_tp2]
    * **Take Profit 3:** $[harga_tp3]

    ---
    📊 **Ringkasan Analisis**

    * **Analisa Candle & Chart Pattern:** [Analisis ringkas Anda di sini. Sebutkan pola yang teridentifikasi.]
    * **Analisa Data Pasar:** [Analisis ringkas berdasarkan Funding Rate dan Long/Short Ratio.]
    """

    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.6}}

    try:
        res = requests.post(url, headers=headers, json=body, timeout=60)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Error saat menghubungi Gemini API: {e}")
        return f"Terjadi kesalahan pada layanan AI: {e}"