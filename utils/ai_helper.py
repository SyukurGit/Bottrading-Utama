# utils/ai_helper.py
import requests
import json
from config import GEMINI_API_KEY

def get_professional_analysis(symbol: str, timeframe: str, kline_data: list,
                              funding_rate: str, long_short_ratio: str):
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

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }
    body = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {"temperature": 0.6}
    }

    try:
        res = requests.post(url, headers=headers, json=body, timeout=60)
        res.raise_for_status()
        data = res.json()
        # Guard untuk response kosong
        candidates = data.get("candidates", [])
        if not candidates:
            return f"AI tidak mengembalikan kandidat: {data}"
        return candidates[0]["content"]["parts"][0]["text"]
    except requests.HTTPError as http_err:
        # Log detail respons biar mudah debug
        return f"Terjadi kesalahan pada layanan AI: {http_err} | detail: {getattr(res, 'text', '')[:500]}"
    except Exception as e:
        return f"Terjadi kesalahan pada layanan AI: {e}"
