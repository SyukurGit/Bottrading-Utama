# Botk
by:SyukurGit

Bot Telegram canggih yang menyediakan analisis teknikal pasar kripto secara *real-time*. Dilengkapi dengan visualisasi *candlestick chart* dan analisis mendalam menggunakan Google Gemini AI, bot ini dirancang untuk membantu trader mengambil keputusan yang lebih baik.

## Fitur Utama

- **🤖 Alur Percakapan Interaktif**: Pengguna dipandu melalui menu yang jelas, mulai dari pemilihan token hingga analisis akhir.
- **📈 Visualisasi Chart**: Secara otomatis menghasilkan dan mengirim gambar *candlestick chart* untuk token dan *timeframe* yang dipilih.
- **🧠 Analisis Berbasis AI**: Menggunakan model **Google Gemini** untuk memberikan analisis teknikal, prediksi sentimen pasar, serta rekomendasi sinyal trading (Entry, Take Profit, Stop Loss) berdasarkan data OHLC terbaru.
- **🌐 Data Pasar Real-time**: Terintegrasi langsung dengan **API CoinGecko** untuk mendapatkan data harga Open, High, Low, Close (OHLC) yang akurat.
- **⏳ Cooldown System**: Mencegah *spamming* permintaan analisis dengan memberlakukan jeda waktu antar permintaan untuk setiap pengguna.
- **💾 Database Lokal**: Menggunakan SQLite untuk menyimpan informasi pengguna, seperti waktu analisis terakhir untuk fitur *cooldown*.

## Tampilan Bot

1.  **Pengguna memulai percakapan dan memilih token.**
    *Gambar alur pemilihan token dan timeframe di sini*

2.  **Bot menampilkan chart candlestick dan hasil analisis AI.**
    *Gambar hasil chart dan teks analisis dari bot di sini*

## Teknologi yang Digunakan

- **Bahasa**: Python 3
- **Framework Bot**: `python-telegram-bot`
- **Model AI**: Google Gemini
- **Sumber Data**: CoinGecko API
- **Pembuatan Chart**: `matplotlib`, `mplfinance`, `pandas`
- **Database**: SQLite

## Cara Menggunakan

### Prasyarat

- Python 3.8 atau yang lebih baru
- Akun Telegram dan Token Bot
- Kunci API untuk Google Gemini
- Git

### Instalasi

1.  **Clone repository ini:**
    ```sh
    git clone [URL-REPOSITORY-ANDA]
    cd [NAMA-FOLDER-REPOSITORY]
    ```

2.  **Buat dan aktifkan virtual environment (dianjurkan):**
    ```sh
    python -m venv venv
    source venv/bin/activate  # Di Windows, gunakan: venv\Scripts\activate
    ```

3.  **Install semua dependensi yang dibutuhkan:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Kunci API:**
    - Buka file `config.py`.
    - Masukkan `TELEGRAM_TOKEN` dan `GEMINI_API_KEY` Anda.
    ```python
    # config.py
    TELEGRAM_TOKEN = "7207657126:AAF53TTiNB_VIQcl_8bk5DfYKgZ6laX8izU"  # Ganti dengan token Anda
    GEMINI_API_KEY = "AIzaSyDsc31OGVg2Jwhhcwruqum6k2cef_prByo" # Ganti dengan kunci Gemini Anda
    COINGECKO_API_URL = "[https://api.coingecko.com/api/v3](https://api.coingecko.com/api/v3)"
    COOLDOWN_SECONDS = 180
    ```

### Menjalankan Bot

Setelah semua konfigurasi selesai, jalankan bot dengan perintah:
```sh
python main.py
