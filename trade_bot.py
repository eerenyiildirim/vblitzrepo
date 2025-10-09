import requests, time, numpy as np, warnings
warnings.filterwarnings("ignore")

# ========== TELEGRAM AYARLARI ==========
TELEGRAM_TOKEN = "7968419128:AAESyl20HCyUGM9MpSqforWX8QQm7R9BwdM"
CHAT_ID = "1065616509"

# ========== COINLER ==========
COINS = ["AVAXUSDT","BCHUSDT","HBARUSDT","XRPUSDT",
          "ASTERUSDT","THETAUSDT","REZUSDT","ZENUSDT","ENAUSDT","FORMUSDT",
          "GUNUSDT","HOOKUSDT","PENGUUSDT","OPUSDT","NEARUSDT",
          "SCRTUSDT","THEUSDT","XPLUSDT","LTCUSDT","WLFIUSDT","EIGENUSDT"]

INTERVAL = "1h"
RR_LIMIT = 1.8
VOLUME_LIMIT = 1.2

# ========== TELEGRAM MESAJ GÖNDERME ==========
def telegram_mesaj_gonder(metin):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": metin, "parse_mode": "Markdown"}
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

# ========== RSI, EMA, LEVERAGE ==========
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

# ========== HEDEF TAKİBİ ==========
aktif_islemler = {}

def fiyat_takip_et(coin, fiyat):
    if coin in aktif_islemler:
        tp1, tp2, sl, yön, tp1_hit = aktif_islemler[coin]
        if yön == "LONG":
            if fiyat >= tp1 and not tp1_hit:
                telegram_mesaj_gonder(f"🎯 *{coin} TP1 hedefi gerçekleşti!* (Long)\nFiyat: {fiyat:.4f}")
                aktif_islemler[coin] = (tp1, tp2, sl, yön, True)
            if fiyat >= tp2:
                telegram_mesaj_gonder(f"🏁 *{coin} TP2 hedefi gerçekleşti!* Pozisyon kapatıldı.\nFiyat: {fiyat:.4f}")
                del aktif_islemler[coin]
            if fiyat <= sl:
                telegram_mesaj_gonder(f"🛑 *{coin} Stop Loss tetiklendi.*\nFiyat: {fiyat:.4f}")
                del aktif_islemler[coin]
        elif yön == "SHORT":
            if fiyat <= tp1 and not tp1_hit:
                telegram_mesaj_gonder(f"🎯 *{coin} TP1 hedefi gerçekleşti!* (Short)\nFiyat: {fiyat:.4f}")
                aktif_islemler[coin] = (tp1, tp2, sl, yön, True)
            if fiyat <= tp2:
                telegram_mesaj_gonder(f"🏁 *{coin} TP2 hedefi gerçekleşti!* Pozisyon kapatıldı.\nFiyat: {fiyat:.4f}")
                del aktif_islemler[coin]
            if fiyat >= sl:
                telegram_mesaj_gonder(f"🛑 *{coin} Stop Loss tetiklendi.* (Short)\nFiyat: {fiyat:.4f}")
                del aktif_islemler[coin]

# ========== ANA DÖNGÜ ==========
while True:
    for coin in COINS:
        try:
            closes, volumes = get_klines(coin, INTERVAL)
            if len(closes) < 30:
                print(f"{coin}: Yetersiz veri, atlanıyor.")
                continue

            fiyat = closes[-1]
            ema7, ema25 = ema(closes, 7)[-1], ema(closes, 25)[-1]
            rsi_val = rsi(closes)[-1]
            son_hacim = volumes[-1]
            ort_hacim = np.mean(volumes[-20:])
            hacim_orani = son_hacim / ort_hacim if ort_hacim > 0 else 1

            # Hacim zayıfsa atla
            if hacim_orani < 1.0:
                print(f"{coin}: hacim yetersiz ({hacim_orani:.2f}x), atlandı.")
                continue

            tp_oran, sl_oran = 0.025, 0.015
            tp1 = fiyat * (1 + tp_oran)
            tp2 = fiyat * (1 + (tp_oran * 2))
            sl = fiyat * (1 - sl_oran)
            rr = (tp1 - fiyat) / (fiyat - sl) if fiyat > sl else 0

            if rr < RR_LIMIT:
                print(f"{coin}: düşük R/R ({rr:.2f}), sinyal gönderilmedi.")
                continue

            # Trend gücü farkı (EMA7-EMA25 oranı)
            trend_gucu = abs((ema7 - ema25) / ema25) * 100

            # PREMIUM kontrolü (EMA farkı > 0.5% ve hacim > 1.2x ve RSI güçlü bölgede)
            premium = (
                trend_gucu > 0.5 and
                hacim_orani >= VOLUME_LIMIT and
                ((55 < rsi_val < 67) or (33 < rsi_val < 45))
            )

            # AL sinyali
            if ema7 > ema25 and 55 < rsi_val < 70:
                lev = leverage_onerisi(rsi_val, "LONG")
                icon = "🌟 PREMIUM SİNYAL 🌟" if premium else "📈 AL SİNYALİ"
                mesaj = (f"{icon} — {coin}\n\n"
                         f"💰 Fiyat: {fiyat:.4f}\n📊 RSI: {rsi_val:.2f}\n"
                         f"📈 Trend Gücü: {trend_gucu:.2f}%\n"
                         f"⚙️ Kaldıraç: {lev}\n📊 Hacim: {hacim_orani:.2f}x\n"
                         f"📈 Risk/Ödül: {rr:.2f}\n\n"
                         f"🎯 TP1: {tp1:.4f}\n🎯 TP2: {tp2:.4f}\n🛑 SL: {sl:.4f}")
                telegram_mesaj_gonder(mesaj)
                aktif_islemler[coin] = (tp1, tp2, sl, "LONG", False)

            # SAT sinyali
            elif ema7 < ema25 and 30 < rsi_val < 45:
                tp1_s, tp2_s, sl_s = fiyat * (1 - tp_oran), fiyat * (1 - (tp_oran * 2)), fiyat * (1 + sl_oran)
                rr_s = (fiyat - tp1_s) / (sl_s - fiyat) if sl_s > fiyat else 0
                if rr_s < RR_LIMIT:
                    continue
                lev = leverage_onerisi(rsi_val, "SHORT")
                icon = "🌟 PREMIUM SHORT 🌟" if premium else "📉 SHORT SİNYALİ"
                mesaj = (f"{icon} — {coin}\n\n"
                         f"💰 Fiyat: {fiyat:.4f}\n📊 RSI: {rsi_val:.2f}\n"
                         f"📉 Trend Gücü: {trend_gucu:.2f}%\n"
                         f"⚙️ Kaldıraç: {lev}\n📊 Hacim: {hacim_orani:.2f}x\n"
                         f"📈 Risk/Ödül: {rr_s:.2f}\n\n"
                         f"🎯 TP1: {tp1_s:.4f}\n🎯 TP2: {tp2_s:.4f}\n🛑 SL: {sl_s:.4f}")
                telegram_mesaj_gonder(mesaj)
                aktif_islemler[coin] = (tp1_s, tp2_s, sl_s, "SHORT", False)

            fiyat_takip_et(coin, fiyat)
            time.sleep(0.5)

        except Exception as e:
            print(f"{coin} hata: {e}")
            continue

    time.sleep(300)
