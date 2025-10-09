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
"AVAXUSDT","BCHUSDT","HBARUSDT","XRPUSDT",
"ASTERUSDT","THETAUSDT","REZUSDT","ZENUSDT","ENAUSDT","FORMUSDT",
"GUNUSDT","HOOKUSDT","PENGUUSDT","OPUSDT","NEARUSDT",
"SCRTUSDT","THEUSDT","XPLUSDT","LTCUSDT","WLFIUSDT","EIGENUSDT"
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

# ========== GEÇMİŞ KAYIT ==========
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

# Başlık satırı (sadece 1 kere oluşturur)
try:
    with open("trade_history.csv", "x", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Zaman", "Coin", "Yön", "Giriş", "TP1", "TP2", "SL", "Hedef", "Sonuç", "Süre (saat)"])
except FileExistsError:
    pass

# ========== HEDEF TAKİBİ ==========
aktif_islemler = {}

def fiyat_takip_et(coin, fiyat, closes):
    if coin in aktif_islemler:
        tp1, tp2, sl, yön, tp1_hit = aktif_islemler[coin]
        tahmini_sure = tahmini_sure_hesapla(closes, fiyat, tp1)
        if np.random.randint(0, 10) == 0:
            telegram_mesaj_gonder(
                f"🔁 *{coin} Güncellemesi:*\n"
                f"💰 Fiyat: {fiyat:.4f}\n"
                f"⏱ Kalan TP1 Süresi: {tahmini_sure}\n"
                f"🎯 TP1: {tp1:.4f} | TP2: {tp2:.4f} | 🛑 SL: {sl:.4f}"
            )

        if yön == "LONG":
            if fiyat >= tp1 and not tp1_hit:
                telegram_mesaj_gonder(f"🎯 *{coin} TP1 gerçekleşti!* (Long)\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "TP1", "✅ Kazanç", 0)
                aktif_islemler[coin] = (tp1, tp2, sl, yön, True)
            if fiyat >= tp2:
                telegram_mesaj_gonder(f"🏁 *{coin} TP2 gerçekleşti!* Pozisyon kapatıldı.\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "TP2", "✅ Kazanç", 0)
                del aktif_islemler[coin]
            if fiyat <= sl:
                telegram_mesaj_gonder(f"🛑 *{coin} Stop Loss tetiklendi.*\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "SL", "❌ Zarar", 0)
                del aktif_islemler[coin]

        elif yön == "SHORT":
            if fiyat <= tp1 and not tp1_hit:
                telegram_mesaj_gonder(f"🎯 *{coin} TP1 gerçekleşti!* (Short)\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "TP1", "✅ Kazanç", 0)
                aktif_islemler[coin] = (tp1, tp2, sl, yön, True)
            if fiyat <= tp2:
                telegram_mesaj_gonder(f"🏁 *{coin} TP2 gerçekleşti!* Pozisyon kapatıldı.\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "TP2", "✅ Kazanç", 0)
                del aktif_islemler[coin]
            if fiyat >= sl:
                telegram_mesaj_gonder(f"🛑 *{coin} Stop Loss tetiklendi.* (Short)\nFiyat: {fiyat:.4f}")
                kaydet_islem(coin, yön, fiyat, tp1, tp2, sl, "SL", "❌ Zarar", 0)
                del aktif_islemler[coin]

# ========== GÜNLÜK RAPOR ==========
def gundelik_rapor_gonder():
    try:
        df = pd.read_csv("trade_history.csv")
        df["Zaman"] = pd.to_datetime(df["Zaman"])
        bugun = datetime.now().date()
        df_gunluk = df[df["Zaman"].dt.date == bugun]
        if df_gunluk.empty:
            return
        toplam = len(df_gunluk)
        tp1 = len(df_gunluk[df_gunluk["Hedef"] == "TP1"])
        tp2 = len(df_gunluk[df_gunluk["Hedef"] == "TP2"])
        sl = len(df_gunluk[df_gunluk["Hedef"] == "SL"])
        basari = ((tp1 + tp2) / toplam) * 100
        ort_sure = df_gunluk["Süre (saat)"].replace(0, np.nan).mean()
        ort_sure = f"{ort_sure:.1f}" if not np.isnan(ort_sure) else "Belirsiz"
        mesaj = (
            f"📅 *Günlük Performans Özeti — {bugun.strftime('%d %B %Y')}*\n\n"
            f"🔹 Toplam sinyal: {toplam}\n✅ TP1: {tp1}\n🏁 TP2: {tp2}\n❌ SL: {sl}\n\n"
            f"📈 Başarı: %{basari:.1f}\n⏱ Ortalama TP süresi: {ort_sure} saat"
        )
        telegram_mesaj_gonder(mesaj, premium=True)
    except Exception as e:
        print("Rapor oluşturulamadı:", e)

# ========== HAFTALIK RAPOR ==========
def haftalik_rapor_gonder():
    try:
        df = pd.read_csv("trade_history.csv")
        df["Zaman"] = pd.to_datetime(df["Zaman"])
        bugun = datetime.now()
        baslangic = bugun - timedelta(days=bugun.weekday() + 7)
        bitis = baslangic + timedelta(days=7)
        df_haftalik = df[(df["Zaman"] >= baslangic) & (df["Zaman"] < bitis)]
        if df_haftalik.empty:
            return
        toplam = len(df_haftalik)
        tp1 = len(df_haftalik[df_haftalik["Hedef"] == "TP1"])
        tp2 = len(df_haftalik[df_haftalik["Hedef"] == "TP2"])
        sl = len(df_haftalik[df_haftalik["Hedef"] == "SL"])
        basari = ((tp1 + tp2) / toplam) * 100
        ort_sure = df_haftalik["Süre (saat)"].replace(0, np.nan).mean()
        ort_sure = f"{ort_sure:.1f}" if not np.isnan(ort_sure) else "Belirsiz"
        mesaj = (
            f"📆 *Haftalık Performans Özeti — {baslangic.strftime('%d %b')} - {bitis.strftime('%d %b %Y')}*\n\n"
            f"🔹 Toplam işlem: {toplam}\n✅ TP1: {tp1}\n🏁 TP2: {tp2}\n❌ SL: {sl}\n\n"
            f"📈 Başarı: %{basari:.1f}\n⏱ Ortalama TP süresi: {ort_sure} saat"
        )
        telegram_mesaj_gonder(mesaj, premium=True)
    except Exception as e:
        print("Haftalık rapor hatası:", e)

# ========== ANA DÖNGÜ ==========
while True:
    for coin in COINS:
        try:
            closes, volumes = get_klines(coin, INTERVAL)
            if len(closes) < 30:
                continue
            fiyat = closes[-1]
            ema7, ema25 = ema(closes, 7)[-1], ema(closes, 25)[-1]
            rsi_val = rsi(closes)[-1]
            son_hacim = volumes[-1]
            ort_hacim = np.mean(volumes[-20:])
            hacim_orani = son_hacim / ort_hacim if ort_hacim > 0 else 1
            if hacim_orani < 1.0:
                continue
            tp_oran, sl_oran = 0.025, 0.015
            tp1 = fiyat * (1 + tp_oran)
            tp2 = fiyat * (1 + (tp_oran * 2))
            sl = fiyat * (1 - sl_oran)
            rr = (tp1 - fiyat) / (fiyat - sl) if fiyat > sl else 0
            if rr < RR_LIMIT:
                continue
            trend_gucu = abs((ema7 - ema25) / ema25) * 100
            premium = (
                trend_gucu > 0.5 and hacim_orani >= VOLUME_LIMIT and
                ((55 < rsi_val < 67) or (33 < rsi_val < 45))
            )
            tahmini_sure = tahmini_sure_hesapla(closes, fiyat, tp1)

            # LONG SİNYALİ
            if ema7 > ema25 and 55 < rsi_val < 70:
                lev = leverage_onerisi(rsi_val, "LONG")
                icon = "🌟 PREMIUM SİNYAL 🌟" if premium else "📈 AL SİNYALİ"
                mesaj = (
                    f"{icon} — {coin}\n\n💰 Fiyat: {fiyat:.4f}\n📊 RSI: {rsi_val:.2f}\n"
                    f"📈 Trend Gücü: {trend_gucu:.2f}%\n📊 Hacim: {hacim_orani:.2f}x\n"
                    f"⚙️ Kaldıraç: {lev}\n📈 Risk/Ödül: {rr:.2f}\n"
                    f"⏱ Ortalama TP1 Süresi: {tahmini_sure}\n\n🎯 TP1: {tp1:.4f}\n🎯 TP2: {tp2:.4f}\n🛑 SL: {sl:.4f}"
                )
                telegram_mesaj_gonder(mesaj, premium=premium)
                aktif_islemler[coin] = (tp1, tp2, sl, "LONG", False)

            # SHORT SİNYALİ
            elif ema7 < ema25 and 30 < rsi_val < 45:
                tp1_s, tp2_s, sl_s = fiyat * (1 - tp_oran), fiyat * (1 - (tp_oran * 2)), fiyat * (1 + sl_oran)
                rr_s = (fiyat - tp1_s) / (sl_s - fiyat) if sl_s > fiyat else 0
                if rr_s < RR_LIMIT:
                    continue
                lev = leverage_onerisi(rsi_val, "SHORT")
                tahmini_sure = tahmini_sure_hesapla(closes, fiyat, tp1_s)
                icon = "🌟 PREMIUM SHORT 🌟" if premium else "📉 SHORT SİNYALİ"
                mesaj = (
                    f"{icon} — {coin}\n\n💰 Fiyat: {fiyat:.4f}\n📊 RSI: {rsi_val:.2f}\n"
                    f"📉 Trend Gücü: {trend_gucu:.2f}%\n📊 Hacim: {hacim_orani:.2f}x\n"
                    f"⚙️ Kaldıraç: {lev}\n📈 Risk/Ödül: {rr_s:.2f}\n"
                    f"⏱ Ortalama TP1 Süresi: {tahmini_sure}\n\n🎯 TP1: {tp1_s:.4f}\n🎯 TP2: {tp2_s:.4f}\n🛑 SL: {sl_s:.4f}"
                )
                telegram_mesaj_gonder(mesaj, premium=premium)
                aktif_islemler[coin] = (tp1_s, tp2_s, sl_s, "SHORT", False)

            fiyat_takip_et(coin, fiyat, closes)
           
