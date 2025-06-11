# utils/api_helper.py

import requests
import time
from config import COINGECKO_API_URL
# ===== PERUBAHAN DIMULAI DI SINI =====
from utils.coin_list import get_id_from_symbol
# ===== PERUBAHAN SELESAI =====

# Definisikan URL API untuk Spot dan Futures
BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/klines"
BINANCE_FUTURES_API_URL = "https://fapi.binance.com" # Untuk Funding Rate & Long/Short

def get_coingecko_coin_data(symbol: str):
    """Mengambil data profil koin dari CoinGecko API."""
    
    # ===== PERUBAHAN DIMULAI DI SINI =====
    # Cari ID koin secara dinamis dari daftar yang sudah dimuat
    coin_id = get_id_from_symbol(symbol)
    if not coin_id:
        return None # Token tidak ditemukan di daftar master
    # ===== PERUBAHAN SELESAI =====

    params = {
        'localization': 'false',
        'tickers': 'false',
        'market_data': 'true',
        'community_data': 'false',
        'developer_data': 'false',
        'sparkline': 'false'
    }

    try:
        url = f"{COINGECKO_API_URL}/coins/{coin_id}"
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        
        description = data.get('description', {}).get('en', 'Tidak ada deskripsi.')
        # Ambil beberapa kalimat pertama untuk ringkasan
        if description:
            sentences = description.split('. ')
            short_description = '. '.join(sentences[:2])
            if not short_description.endswith('.'):
                short_description += '.'
        else:
            short_description = 'Tidak ada deskripsi.'

        profile_data = {
            "name": data.get('name', 'N/A'),
            "description": short_description,
            "market_cap": data.get('market_data', {}).get('market_cap', {}).get('usd', 0),
            "total_volume": data.get('market_data', {}).get('total_volume', {}).get('usd', 0),
            "total_supply": data.get('market_data', {}).get('total_supply', 0),
            "current_price": data.get('market_data', {}).get('current_price', {}).get('usd', 0)
        }
        return profile_data
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengambil data dari CoinGecko untuk ID {coin_id}: {e}")
        return None

def get_binance_kline_data(symbol: str, timeframe: str):
    """Mengambil data Kline (OHLCV) dari Binance Spot API."""
    interval_map = {'1h': '1h', '24h': '4h', '7d': '1d'}
    interval = interval_map.get(timeframe, '1h')
    formatted_symbol = symbol.upper() + "USDT"
    params = {'symbol': formatted_symbol, 'interval': interval, 'limit': 100}
    
    try:
        res = requests.get(BINANCE_SPOT_API_URL, params=params)
        res.raise_for_status()
        processed_data = [{"time": k[0], "open": float(k[1]), "high": float(k[2]), "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])} for k in res.json()]
        return processed_data
    except requests.exceptions.RequestException as e:
        print(f"Gagal mengambil data Kline dari Binance: {e}")
        return None

def get_funding_rate(symbol: str):
    """Mengambil Funding Rate terakhir dari Binance Futures."""
    params = {'symbol': symbol.upper() + "USDT"}
    try:
        res = requests.get(f"{BINANCE_FUTURES_API_URL}/fapi/v1/premiumIndex", params=params)
        res.raise_for_status()
        data = res.json()
        return f"{float(data['lastFundingRate']) * 100:.4f}%"
    except requests.exceptions.RequestException:
        return "Tidak tersedia"

def get_long_short_ratio(symbol: str):
    """Mengambil Global Long/Short Ratio dari Binance Futures."""
    params = {
        'symbol': symbol.upper() + "USDT",
        'period': '5m',
        'limit': 1
    }
    try:
        res = requests.get(f"{BINANCE_FUTURES_API_URL}/futures/data/globalLongShortAccountRatio", params=params)
        res.raise_for_status()
        data = res.json()
        if data:
            return f"{float(data[0]['longShortRatio']):.2f} (Long: {float(data[0]['longAccount'])*100:.1f}%, Short: {float(data[0]['shortAccount'])*100:.1f}%)"
        return "Tidak tersedia"
    except requests.exceptions.RequestException:
        return "Tidak tersedia"