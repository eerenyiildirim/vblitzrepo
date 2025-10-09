# ========== OTOMATİK MODÜL YÜKLEYİCİ ==========
import importlib, subprocess, sys


def ensure_package(pkg):
    try:
        importlib.import_module(pkg)
    except ImportError:
        print(f"📦 {pkg} bulunamadı, yükleniyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


for package in ["requests", "numpy", "pandas"]:
    ensure_package(package)

# ========== NORMAL IMPORTLAR ==========
import requests, time, numpy as np, pandas as pd, csv, warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ========== TELEGRAM AYARLARI ==========
TELEGRAM_TOKEN = "7968419128:AAESyl20HCyUGM9MpSqforWX8QQm7R9BwdM"
CHAT_ID = "1065616509"

# ========== COINLER ==========
COINS = [
    "AVAXUSDT", "BCHUSDT", "HBARUSDT", "XRPUSDT", "ASTERUSDT", "THETAUSDT",
    "REZUSDT", "ZENUSDT", "ENAUSDT", "FORMUSDT", "GUNUSDT", "HOOKUSDT",
    "PENGUUSDT", "OPUSDT", "NEARUSDT", "SCRTUSDT", "THEUSDT", "XPLUSDT",
    "LTCUSDT", "WLFIUSDT", "EIGENUSDT"
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
        return closes, volu
