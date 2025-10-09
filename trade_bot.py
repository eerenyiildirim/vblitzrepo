import requests, time, numpy as np, pandas as pd, csv, warnings
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")

# ========== TELEGRAM AYARLARI ==========
TELEGRAM_TOKEN = "7968419128:AAESyl20HCyUGM9MpSqforWX8QQm7R9BwdM"
CHAT_ID = "1065616509"

# ========== COINLER ==========
COINS = ["AVAXUSDT","BCHUSDT","HBARUSDT","XRPUSDT",
          "ASTERUSDT","THETAUSDT","REZUSDT","ZENUSDT","ENAUSDT","FORMUSDT",
          "GUNUSDT","HOOKUSDT","PENGUUSDT","OPUSDT","NEARUSDT",
          "SCRTUSDT","THEUSDT","XPLUSDT","LTCUSDT","WLFIUSDT","EIGENUSDT"]
]

INTERVAL = "1h"
RR_LIMIT = 1.8
VOLUME_LIMIT = 1.2

# ========== TELEGRAM MESAJ GÖNDERME ==========
def telegram_mesaj_gonder(metin, premium=False):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": metin,
        "parse_mode": "Markdown",
        "disable_notification": False if premium else True
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram mesaj hatası:", e)

# ========== VERİ ALIMI (BINANCE) ==========
def get_klines(symbol, interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    if isinstance(data, list) and len(data) > 0:
        closes = np.array([float(x[4]) for x in data])
        volumes = np.array([float(x[5]) for x in data])
        return closes, volumes
    raise ValueError(f"{symbol} için veri alınamadı")

# ========== TEKNİK HESAPLAR ==========
def rsi(data, period=14):
    delta = np.diff(data)
    gain = np.maximum(delta, 0)
    loss = np.maximum(-delta, 0)
    avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))

def ema(data, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    ema_data = np.convolve(data, weights, mode='full')[:len(data)]
    ema_data[:window] = ema_data[window]
    return ema_data

def leverage_onerisi(rsi_val, yön):
    if yön == "LONG":
        if rsi_val < 60: return "3x – 5x (güvenli giriş)"
        elif rsi_val < 65: return "6x – 8x (orta trend)"
        elif rsi_val < 70: return "9x – 12x (güçlü trend)"
        else: return "2x – 3x (aşırı alım, dikkatli ol)"
    elif yön == "SHORT":
        if rsi_val > 45: return "3x – 5x (zayıf short)"
        elif rsi_val > 35: return "6x – 8x (sağlam short)"
        else: return "9x – 12x (güçlü düşüş trendi)"
    return "5x"

# ========== TP SÜRESİ TAHMİNİ ==========
def tahmini_sure_hesapla(closes, fiyat, tp1):
    son_farklar = np.abs(np.diff(closes[-20:]) / closes[-20:-1])
    ort_hiz = np.mean(son_farklar)
    if ort_hiz == 0:
        return "Belirsiz"
    hedef_fark = abs((tp1 - fiyat) / fiyat)
    mum_sayisi = hedef_fark / ort_hiz
    saat = mum_sayisi * 1
    if saat < 1:
        dk = int(saat * 60)
        return f"≈ {dk} dk"
    elif saat < 24:
        return f"≈ {saat:.1f} saat"
    else:
        gun = saat / 24
        return f"≈ {gun:.1f} gün"

# ========== GEÇMİŞ KAYIT SİSTEMİ ==========
def kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, hedef, sonuc, sure_saat):
    try:
        with open("trade_history.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                coin, yön, f"{fiyat:.4f}", f"{tp1:.4f}", f"{tp2:.4f}",
                f"{sl:.4f}", hedef, sonuc, f"{sure_saat:.2f}"
            ])
    except Exception as e:
        print("📁 İşlem geçmişi kaydedilemedi:", e)

# Başlık satırı oluştur
try:
    with open("trade_history.csv", "x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Zaman", "Coin", "Yön", "Giriş", "TP1", "TP2", "SL"]()
