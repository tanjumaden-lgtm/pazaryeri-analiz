import streamlit as st
import pandas as pd
import io
import os
import json

# --- 1. SİSTEM AYARLARI VE DOSYA YOLLARI ---
st.set_page_config(page_title="Pazaryeri ERP Kar Yönetimi", layout="wide")

# Verilerin kalıcı olarak saklanacağı dosyalar
DATA_DIR = "erp_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

COSTS_FILE = os.path.join(DATA_DIR, "master_costs.csv")
SHIPPING_FILE = os.path.join(DATA_DIR, "master_shipping.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# --- 2. YARDIMCI FONKSİYONLAR (HAFIZA YÖNETİMİ) ---
def save_master_data(df, file_path):
    df.to_csv(file_path, index=False)

def load_master_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {'tr_sabit': 15.0, 'hb_sabit': 15.0, 'hb_tahsilat': 0.008, 'iade_oran': 5.0, 'api_key': ''}

# --- 3. HESAP MOTORU (KIRMIZI ÇİZGİ) ---
def to_float(val):
    if pd.isna(val) or val == "": return 0.0
    if isinstance(val, (int, float)): return float(val)
    res = str(val).replace('TL', '').replace('%', '').replace('.', '').replace(',', '.').strip()
    try: return float(res)
    except: return 0.0

def kargo_hesapla(desi, kargo_df):
    if kargo_df is None: return 0.0
    try:
        desi_val = to_float(desi)
        if desi_val <= 0: return 0.0
        kargo_df.columns = kargo_df.columns.str.strip()
        kargo_df['DESİ'] = kargo_df['DESİ'].apply(to_float)
        if desi_val <= 30:
            matched = kargo_df[kargo_df['DESİ'] >= desi_val].sort_values('DESİ')
            return float(matched.iloc[0]['Fiyat']) if not matched.empty else 447.06
        else:
            return 447.06 + ((float(desi_val) - 30) * 14.87)
    except: return 0.0

# --- 4. SESSION INITIALIZATION ---
if 'processed_df' not in st.session_state: st.session_state.processed_df = None
settings = load_settings()

# --- 5. SOL MENÜ NAVİGASYON (MELONTİK STİLİ) ---
st.sidebar.title("💎 ERP Kar Yönetimi")
st.sidebar.markdown("---")
menu = st.sidebar.radio("DEPARTMANLAR", 
    ["🏠 Dashboard", 
     "📂 Veri Aktarım Merkezi", 
     "📋 Kar Analiz Merkezi", 
     "📦 Envanter (Master Data)", 
     "🚛 Lojistik Operasyon", 
     "🎯 Strateji & Kampanya", 
     "⚙️ Sistem Ayarları"])

# --- 6. ENVANTER (MASTER DATA) - KALICI HAFIZA ---
if menu == "📦 Envanter (Master Data)":
    st.header("📦 Envanter ve Maliyet (Ana Veri)")
    st.info("Alış fiyatlarınızı ve ürün bilgilerinizi buradan bir kez yükleyin. Sistem bunları kalıcı olarak saklar.")
    
    m_f = st.file_uploader("Maliyet Listesini Güncelle (.xlsx)", type=['xlsx'])
    if m_f:
        new_costs = pd.read_excel(m_f)
        new_costs.columns = new_costs.columns.str.strip()
        save_master_data(new_costs, COSTS_FILE)
        st.success("✅ Maliyet veritabanı güncellendi ve kilitlendi!")

    current_costs = load_master_data(COSTS_FILE)
    if current_costs is not None:
        st.subheader("Veritabanındaki Kayıtlı Ürünler")
        st.dataframe(current_costs, use_container_width=True)
        if st.button("Hafızayı Sıfırla (Tüm Maliyetleri Sil)"):
            os.remove(COSTS_FILE)
            st.rerun()

# --- 7. LOJİSTİK OPERASYON - KALICI HAFIZA ---
elif menu == "🚛 Lojistik Operasyon":
    st.header("🚛 Lojistik ve İade Yönetimi")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("Kargo Fiyat Listesi")
        k_f = st.file_uploader("Güncel Kargo Listesini Yükle", type=['xlsx'])
        if k_f:
            new_shipping = pd.read_excel(k_f)
            new_shipping.columns = new_shipping.columns.str.strip()
            save_master_data(new_shipping, SHIPPING_FILE)
            st.success("✅ Kargo tablosu hafızaya alındı!")
        
        current_shipping = load_master_data(SHIPPING_FILE)
        if current_shipping is not None:
            st.write("Kayıtlı Kargo Tablosu:")
            st.dataframe(current_shipping)
    
    with col_l2:
        st.subheader("İade Risk Yönetimi")
        settings['iade_oran'] = st.slider("Tahmini İade Oranı (%)", 0, 25, int(settings['iade_oran']))
        if st.button("İade Oranını Kaydet"):
            save_settings(settings)
            st.success("Kaydedildi.")

# --- 8. VERİ AKTARIM MERKEZİ (GÜNLÜK RAPORLAR) ---
elif menu == "📂 Veri Aktarım Merkezi":
    st.header("📂 Günlük Satış Raporu Aktarımı")
    master_costs = load_master_data(COSTS_FILE)
    master_shipping = load_master_data(SHIPPING_FILE)

    if master_costs is None or master_shipping is None:
        st.error("⚠️ Analiz yapabilmek için önce 'Envanter' ve 'Lojistik' menülerinden ana verileri yüklemelisiniz!")
    else:
        st.success("✅ Sistem Hafızası Hazır. Sadece günlük satış raporlarını yükleyin.")
        c1, c2 = st.columns(2)
        with c1: tr_f = st.file_uploader("Trendyol Satış Raporu", type=['xlsx'])
        with c2: hb_f = st.file_uploader("Hepsiburada Satış Raporu", type=['xlsx'])
        
        if st.button("ANALİZİ BAŞLAT 🚀"):
            if tr_f and hb_f:
                df_tr = pd.read_excel(tr_f); df_hb = pd.read_excel(hb_f)
                for d in [df_tr, df_hb]: d.columns = d.columns.str.strip()
                
                res = []
                # Trendyol Hesaplama
                for _, r in df_tr.iterrows():
                    m_match = master_costs[(master_costs['Barkod'].astype(str) == str(r.get('Barkod'))) | (master_costs['StokKodu'].astype(str) == str(r.get('Tedarikçi Stok Kodu'))) | (master_costs['Ürün Adı'].astype(str) == str(r.get('Ürün Adı')))]
                    if not m_match.empty:
                        alis = to_float(m_match.iloc[0].get('Alış Fiyatı', 0)); satis = to_float(r.get("Trendyol'da Satılacak Fiyat (KDV Dahil)", 0))
                        desi = to_float(r.get('Desi', m_match.iloc[0].get('Desi', 0))); kargo = kargo_hesapla(desi, master_shipping)
                        kom_tl = satis * (to_float(r.get('Komisyon Oranı', 0)) / 100); iade = kargo * (settings['iade_oran'] / 100)
                        toplam_m = alis + kom_tl + kargo + settings['tr_sabit'] + iade
                        res.append({"Platform": "Trendyol", "Marka": r.get('Marka','-'), "Kod": r.get('Tedarikçi Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": to_float(r.get('Komisyon Oranı', 0)), "Komisyon TL": kom_tl, "Tahsilat Bedeli (TL)": 0.0, "Desi": desi, "Gidiş Kargo": kargo, "Sabit Gider": settings['tr_sabit'], "İade Karşılığı (TL)": iade, "TOPLAM MALİYET": toplam_m, "NET KAR": satis - toplam_m, "Kar Marjı %": ((satis - toplam_m)/satis)*100 if satis > 0 else 0})

                # Hepsiburada Hesaplama
                for _, r in df_hb.iterrows():
                    m_match = master_costs[(master_costs['Barkod'].astype(str) == str(r.get('Barkod'))) | (master_costs['StokKodu'].astype(str) == str(r.get('Satıcı Stok Kodu'))) | (master_costs['Ürün Adı'].astype(str) == str(r.get('Ürün Adı')))]
                    if not m_match.empty:
                        alis = to_float(m_match.iloc[0].get('Alış Fiyatı', 0)); satis = to_float(r.get('Fiyat', 0))
                        kom_o = to_float(r.get('Komisyon Oranı', 0)) * 1.20; kom_tl = satis * (kom_o / 100)
                        tahs = satis * settings['hb_tahsilat']; desi = to_float(m_match.iloc[0].get('Desi', 0)); kargo = kargo_hesapla(desi, master_shipping)
                        iade = (kargo * 2) * (settings['iade_oran'] / 100); toplam_m = alis + kom_tl + tahs + kargo + settings['hb_sabit'] + iade
                        res.append({"Platform": "Hepsiburada", "Marka": r.get('Marka','-'), "Kod": r.get('Satıcı Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": kom_o, "Komisyon TL": kom_tl, "Tahsilat Bedeli (TL)": tahs, "Desi": desi, "Gidiş Kargo": kargo, "Sabit Gider": settings['hb_sabit'], "İade Karşılığı (TL)": iade, "TOPLAM MALİYET": toplam_m, "NET KAR": satis - toplam_m, "Kar Marjı %": ((satis - toplam_m)/satis)*100 if satis > 0 else 0})
                
                st.session_state.processed_df = pd.DataFrame(res)
                st.success("✅ Analiz hazır!")

# --- 9. DASHBOARD VE DİĞERLERİ (MEVCUT YAPI KORUNDU) ---
elif menu == "🏠 Dashboard":
    st.header("🏠 Finansal Durum Özeti")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        c1, c2, c3 = st.columns(3); c1.metric("Toplam Net Kar", f"{df['NET KAR'].sum():,.2f} TL"); c2.metric("Toplam Ciro", f"{df['Satış Fiyatı'].sum():,.2f} TL"); c3.metric("Ortalama Marj", f"%{df['Kar Marjı %'].mean():.2f}")
        st.divider()
        st.write("### Marka Bazlı Kar Dağılımı")
        st.bar_chart(df.groupby('Marka')['NET KAR'].sum())
    else: st.warning("Veri Merkezi'nden analiz yapın.")

elif menu == "📋 Kar Analiz Merkezi":
    st.header("📋 Detaylı Kar Listesi")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        cols = ["Platform", "Marka", "Kod", "Ürün", "Satış Fiyatı", "Alış Maliyeti", "Komisyon %", "Komisyon TL", "Tahsilat Bedeli (TL)", "Desi", "Gidiş Kargo", "Sabit Gider", "İade Karşılığı (TL)", "TOPLAM MALİYET", "NET KAR", "Kar Marjı %"]
        st.dataframe(df[cols].sort_values("NET KAR", ascending=False), use_container_width=True)
    else: st.warning("Veri bulunamadı.")

elif menu == "⚙️ Sistem Ayarları":
    st.header("⚙️ ERP Sistem Ayarları")
    settings['tr_sabit'] = st.number_input("Trendyol Sabit Gider", value=settings['tr_sabit'])
    settings['hb_sabit'] = st.number_input("HB Sabit Gider", value=settings['hb_sabit'])
    settings['hb_tahsilat'] = st.number_input("HB Tahsilat Oranı (%)", value=settings['hb_tahsilat']*100)/100
    if st.button("Ayarları Kaydet"):
        save_settings(settings)
        st.success("Ayarlar kilitlendi.")
