# utils/coin_list.py

import requests
from config import COINGECKO_API_URL

def get_id_from_symbol(symbol: str) -> str | None:
    """
    Mencari ID CoinGecko secara real-time menggunakan endpoint /search.
    Fungsi ini akan mengambil hasil pertama yang paling relevan dari pencarian.
    """
    print(f"Mencari ID CoinGecko untuk simbol: {symbol}...")
    try:
        # Gunakan endpoint /search dari CoinGecko API
        url = f"{COINGECKO_API_URL}/search"
        params = {'query': symbol}
        
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        # Cek apakah 'coins' ada di dalam respons dan tidak kosong
        if data.get('coins') and len(data['coins']) > 0:
            # Ambil ID dari hasil pencarian pertama (paling relevan)
            top_result_id = data['coins'][0]['id']
            print(f"ID yang paling relevan ditemukan: {top_result_id}")
            return top_result_id
        
        print(f"Simbol '{symbol}' tidak ditemukan di CoinGecko.")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"KRITIS: Gagal melakukan pencarian di CoinGecko: {e}")
        return None