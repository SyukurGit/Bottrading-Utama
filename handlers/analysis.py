# handlers/analysis.py

import re
from telegram import ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler
from telegram.error import BadRequest
from utils.cooldown import is_on_cooldown, update_cooldown
# ===== PERUBAHAN DIMULAI DI SINI =====
from utils.api_helper import get_binance_kline_data, get_funding_rate, get_long_short_ratio, get_coingecko_coin_data
# ===== PERUBAHAN SELESAI =====
from utils.ai_helper import get_professional_analysis
from utils.chart_helper import generate_candlestick_chart
import pandas as pd

def parse_analysis_for_levels(text: str) -> dict:
    levels = {}# handlers/analysis.py

import re
from telegram import ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler
from telegram.error import BadRequest
from utils.cooldown import is_on_cooldown, update_cooldown
from utils.api_helper import get_binance_kline_data, get_funding_rate, get_long_short_ratio, get_coingecko_coin_data
from utils.ai_helper import get_professional_analysis
from utils.chart_helper import generate_candlestick_chart

def parse_analysis_for_levels(text: str) -> dict:
    levels = {}
    patterns = {
        'entry': r"Entry Price.*?\$\s*([\d,]+\.?\d*)",
        'sl': r"Stop Loss.*?\$\s*([\d,]+\.?\d*)",
        'tp1': r"Take Profit 1.*?\$\s*([\d,]+\.?\d*)",
        'tp2': r"Take Profit 2.*?\$\s*([\d,]+\.?\d*)",
        'tp3': r"Take Profit 3.*?\$\s*([\d,]+\.?\d*)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                levels[key] = float(price_str)
            except (ValueError, IndexError):
                continue
    return levels

async def start_analysis_callback(update, context):
    query = update.callback_query
    await query.answer("Memproses analisis lengkap...")

    try:
        user_id = query.from_user.id
        if is_on_cooldown(user_id):
            await query.edit_message_text("⚠️ Anda harus menunggu cooldown selesai.")
            return

        token_input = context.user_data.get('token')
        timeframe_value = context.user_data.get('timeframe')
        timeframe_display_map = context.user_data.get('TIMEFRAMES', {})
        timeframe_display = [k for k, v in timeframe_display_map.items() if v == timeframe_value][0] or timeframe_value

        await query.edit_message_text(f"Mencari profil untuk {token_input.upper()} di CoinGecko...")
        
        coin_profile = get_coingecko_coin_data(token_input)
        
        if not coin_profile:
            await query.edit_message_text(f"❌ Gagal menemukan token dengan simbol `{token_input.upper()}`. Pastikan simbol sudah benar.")
            return

        binance_symbol = coin_profile.get("binance_symbol")
        
        # Susun teks profil dan format angka
        def format_number(num):
            if num is None or num == 0: return "N/A"
            if num > 1: return f"${num:,.2f}"
            return f"${num:,.8f}"

        profile_text = (
            f"** > > {coin_profile['name']} ({token_input.upper()})**\n\n"
            f"{coin_profile['description']}\n\n"
            f"▪️ **Harga Sekarang :** `{format_number(coin_profile['current_price'])}`\n"
            f"▪️ **Kapitalisasi Pasar :** `{format_number(coin_profile['market_cap'])}`\n"
            f"▪️ **Volume Perdagangan (24j) :** `{format_number(coin_profile['total_volume'])}`\n"
            f"▪️ **Total Supply :** `{int(coin_profile['total_supply']):,}`"
        )
        
        # Kirim sebagai foto jika ada URL logo, jika tidak, kirim sebagai teks biasa
        image_url = coin_profile.get("image_url")
        if image_url:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=image_url,
                caption=profile_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id, 
                text=profile_text, 
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Jika tidak ditemukan di Binance, hentikan alur dan beri tahu pengguna
        if not binance_symbol:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"ℹ️ Info: Token `{token_input.upper()}` ditemukan di CoinGecko, tetapi tidak ditemukan pasangan trading USDT di Binance. Analisis teknikal tidak dapat dilanjutkan.",
                parse_mode=ParseMode.MARKDOWN
            )
            keyboard = [["Pilih Token Lain"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await context.bot.send_message(chat_id=query.message.chat_id, text="Silakan mulai lagi.", reply_markup=reply_markup)
            return

        # Lanjutkan alur analisis teknikal
        await context.bot.send_message(
            chat_id=query.message.chat_id, 
            text=f"Mengambil data pasar dari Binance untuk {binance_symbol.upper()}/USDT..."
        )
            
        kline_data = get_binance_kline_data(binance_symbol, timeframe_value)

        if not kline_data:
            error_message = f"Gagal mendapatkan data candlestick dari Binance untuk `{binance_symbol.upper()}`. Walaupun ditemukan di CoinGecko, mungkin ada masalah dengan API Binance saat ini."
            await context.bot.send_message(text=error_message, chat_id=query.message.chat_id, parse_mode=ParseMode.MARKDOWN)
            return

        funding_rate = get_funding_rate(binance_symbol)
        long_short_ratio = get_long_short_ratio(binance_symbol)

        clean_chart_image = generate_candlestick_chart(kline_data, binance_symbol, timeframe_display)
        if clean_chart_image:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=clean_chart_image, caption=f"Chart Candlestick > {binance_symbol.upper()}/USDT ({timeframe_display})")

        await context.bot.send_message(chat_id=query.message.chat_id, text="Membuat dan Mengumpulkan data laporan analisis ...")
        text_analysis = get_professional_analysis(binance_symbol, timeframe_display, kline_data, funding_rate, long_short_ratio)

        try:
            await context.bot.send_message(chat_id=query.message.chat_id, text=text_analysis, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            await context.bot.send_message(chat_id=query.message.chat_id, text=text_analysis)

        price_levels = parse_analysis_for_levels(text_analysis)
        if price_levels:
            hlines_list, colors_list, styles_list = [], [], []
            level_map = {'entry': ('b', '--'), 'sl': ('r', '--'), 'tp1': ('g', ':'), 'tp2': ('g', ':'), 'tp3': ('g', ':')}
            for key, (color, style) in level_map.items():
                if key in price_levels:
                    hlines_list.append(price_levels[key])
                    colors_list.append(color)
                    styles_list.append(style)

            if hlines_list:
                hlines_data_for_chart = dict(hlines=hlines_list, colors=colors_list, linestyles=styles_list)

                annotated_chart_image = generate_candlestick_chart(
                    kline_data,
                    binance_symbol,
                    timeframe_display,
                    hlines_data=hlines_data_for_chart
                )

                if annotated_chart_image:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=annotated_chart_image, caption="Chart dengan Anotasi Level Sinyal")

        update_cooldown(user_id)

        keyboard = [["Pilih Token Lain"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(chat_id=query.message.chat_id, text="Analisis selesai.", reply_markup=reply_markup)

    except Exception as e:
        print(f"An error occurred in start_analysis_callback: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Terjadi kesalahan tak terduga: {e}")
    patterns = {
        'entry': r"Entry Price.*?\$\s*([\d,]+\.?\d*)",
        'sl': r"Stop Loss.*?\$\s*([\d,]+\.?\d*)",
        'tp1': r"Take Profit 1.*?\$\s*([\d,]+\.?\d*)",
        'tp2': r"Take Profit 2.*?\$\s*([\d,]+\.?\d*)",
        'tp3': r"Take Profit 3.*?\$\s*([\d,]+\.?\d*)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                price_str = match.group(1).replace(',', '')
                levels[key] = float(price_str)
            except (ValueError, IndexError):
                continue
    return levels

async def start_analysis_callback(update, context):
    query = update.callback_query
    await query.answer("Memproses analisis lengkap...")

    try:
        user_id = query.from_user.id
        if is_on_cooldown(user_id):
            await query.edit_message_text("⚠️ Anda harus menunggu cooldown selesai.")
            return

        token = context.user_data.get('token')
        timeframe_value = context.user_data.get('timeframe')
        timeframe_display_map = context.user_data.get('TIMEFRAMES', {})
        timeframe_display = [k for k, v in timeframe_display_map.items() if v == timeframe_value][0] or timeframe_value

        await query.edit_message_text(f"Mengambil data pasar untuk {token}...")
        
        # ===== BLOK BARU DIMULAI DI SINI =====
        
        # 1. Ambil data profil dari CoinGecko
        coin_profile = get_coingecko_coin_data(token)
        
        # 2. Jika data berhasil didapat, format dan kirim pesannya
        if coin_profile:
            # Fungsi untuk format angka agar mudah dibaca
            def format_number(num):
                if num is None or num == 0:
                    return "N/A"
                if num > 1:
                    return f"${num:,.2f}"
                return f"${num:,.8f}"

            profile_text = (
                f"📊 ** > > {coin_profile['name']} ({token.upper()})**\n\n"
                f"{coin_profile['description']}\n\n"
                f"▪️ **Harga Sekarang :** `{format_number(coin_profile['current_price'])}`\n"
                f"▪️ **Kapitalisasi Pasar :** `{format_number(coin_profile['market_cap'])}`\n"
                f"▪️ **Volume Perdagangan (24j) :** `{format_number(coin_profile['total_volume'])}`\n"
                f"▪️ **Total Supply :** `{int(coin_profile['total_supply']):,}`"
            )
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=profile_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Kirim pesan jika data profil tidak ditemukan, tapi tetap lanjutkan analisis
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"_Info profil untuk {token.upper()} tidak ditemukan, melanjutkan analisis teknikal..._",
                parse_mode=ParseMode.MARKDOWN
            )
            
        # ===== BLOK BARU SELESAI =====
            
        kline_data = get_binance_kline_data(token, timeframe_value)

        if not kline_data:
            error_message = f"Gagal mendapatkan data candlestick dari Binance untuk `{token.upper()}`. Token mungkin tidak valid atau tidak terdaftar."
            await query.edit_message_text(text=error_message, parse_mode=ParseMode.MARKDOWN)
            keyboard = [["Pilih Token Lain"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="Silakan coba lagi dengan token yang berbeda.",
                reply_markup=reply_markup
            )
            return

        funding_rate = get_funding_rate(token)
        long_short_ratio = get_long_short_ratio(token)

        clean_chart_image = generate_candlestick_chart(kline_data, token, timeframe_display)
        if clean_chart_image:
            await context.bot.send_photo(chat_id=query.message.chat_id, photo=clean_chart_image, caption=f"Chart Candlestick > {token.upper()}/USDT ({timeframe_display})")

        await context.bot.send_message(chat_id=query.message.chat_id, text="Membuat dan Mengumpulkan data laporan analisis ...")
        text_analysis = get_professional_analysis(token, timeframe_display, kline_data, funding_rate, long_short_ratio)

        try:
            await context.bot.send_message(chat_id=query.message.chat_id, text=text_analysis, parse_mode=ParseMode.MARKDOWN)
        except BadRequest:
            await context.bot.send_message(chat_id=query.message.chat_id, text=text_analysis)

        price_levels = parse_analysis_for_levels(text_analysis)
        if price_levels:
            hlines_list, colors_list, styles_list = [], [], []
            level_map = {'entry': ('b', '--'), 'sl': ('r', '--'), 'tp1': ('g', ':'), 'tp2': ('g', ':'), 'tp3': ('g', ':')}
            for key, (color, style) in level_map.items():
                if key in price_levels:
                    hlines_list.append(price_levels[key])
                    colors_list.append(color)
                    styles_list.append(style)

            if hlines_list:
                hlines_data_for_chart = dict(hlines=hlines_list, colors=colors_list, linestyles=styles_list)

                annotated_chart_image = generate_candlestick_chart(
                    kline_data,
                    token,
                    timeframe_display,
                    hlines_data=hlines_data_for_chart
                )

                if annotated_chart_image:
                    await context.bot.send_photo(chat_id=query.message.chat_id, photo=annotated_chart_image, caption="Chart dengan Anotasi Level Sinyal")

        update_cooldown(user_id)

        keyboard = [["Pilih Token Lain"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(chat_id=query.message.chat_id, text="Analisis selesai.", reply_markup=reply_markup)

    except Exception as e:
        print(f"An error occurred in start_analysis_callback: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Terjadi kesalahan tak terduga: {e}")