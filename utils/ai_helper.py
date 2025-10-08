# utils/ai_helper.py
import requests, json
from config import GEMINI_API_KEY

# Daftar fallback model yang MASIH hidup per 2025
PREFERRED_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]

def _call_gemini(model: str, prompt: str):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.6}
    }
    res = requests.post(url, headers=headers, json=body, timeout=60)
    res.raise_for_status()
    data = res.json()
    cands = data.get("candidates", [])
    if not cands:
        raise RuntimeError(f"Tidak ada kandidat balasan: {data}")
    return cands[0]["content"]["parts"][0]["text"]

def get_professional_analysis(symbol: str, timeframe: str, kline_data: list,
                              funding_rate: str, long_short_ratio: str):
    recent_kline = kline_data[-50:]
    prompt = f"""
Anda adalah seorang Analis Kripto Profesional...
- Data Candlestick (OHLC): {json.dumps(recent_kline)}
- Funding Rate Saat Ini: {funding_rate}
- Global Long/Short Ratio: {long_short_ratio}

--- TEMPLATE LAPORAN ---
📈 **Hasil Analisa Lengkap untuk {symbol}/USDT ({timeframe})**
* **Entry Price:** $[harga_entry]
* **Stop Loss:** $[harga_sl]
* **Take Profit 1:** $[harga_tp1]
* **Take Profit 2:** $[harga_tp2]
* **Take Profit 3:** $[harga_tp3]
---
📊 **Ringkasan Analisis**
* **Analisa Candle & Chart Pattern:** ...
* **Analisa Data Pasar:** ...
""".strip()

    last_err = None
    for model in PREFERRED_MODELS:
        try:
            return _call_gemini(model, prompt)
        except requests.HTTPError as e:
            # 404/NOT_FOUND → coba model berikutnya
            if e.response is not None and e.response.status_code == 404:
                last_err = f"{model} -> 404"
                continue
            # error lain, langsung lempar detailnya
            detail = e.response.text[:600] if getattr(e, "response", None) else str(e)
            return f"Terjadi kesalahan pada layanan AI: {e} | detail: {detail}"
        except Exception as e:
            last_err = str(e)
            continue
    return f"Gagal memanggil Gemini. Terakhir: {last_err}. Coba cek model aktif dengan ListModels."
