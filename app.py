import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")

# --- MODERN TASARIM (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Pazaryeri Strateji & Kar Yönetim Merkezi")

# --- 1. MATEMATİKSEL FONKSİYONLAR ---
def to_float(val):
    if pd.isna(val) or val == "": return 0.0
    if isinstance(val, (int, float)): return float(val)
    res = str(val).replace('TL', '').replace('%', '').replace('.', '').replace(',', '.').strip()
    try: return float(res)
    except: return 0.0

def kargo_hesapla(desi, kargo_df):
    try:
        desi_val = to_float(desi)
        if desi_val <= 0: return 0.0
        kargo_df.columns = kargo_df.columns.str.strip()
        kargo_df['DESİ'] = kargo_df['DESİ'].apply(to_float)
        if desi_val <= 30:
            matched = kargo_df[kargo_df['DESİ'] >= desi_val].sort_values('DESİ')
            return float(matched.iloc[0]['Fiyat']) if not matched.empty else 447.06
        else:
            return 447.06 + ((desi_val - 30) * 14.87)
    except: return 0.0

# --- 2. GİRİŞ PANELİ ---
with st.sidebar:
    st.header("📂 Veri Girişi")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi", type=['xlsx'])
    
    st.divider()
    st.subheader("⚙️ Gider Ayarları")
    tr_sabit = st.number_input("Trendyol Sabit Gider (TL)", value=15.0)
    hb_sabit = st.number_input("HB Sabit Gider (TL)", value=15.0)
    hb_tahsilat_oran = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100
    
    st.divider()
    st.subheader("🔄 İade Risk Ayarı")
    iade_orani = st.slider("Tahmini İade Oranı (%)", 0, 20, 5)

# --- 3. ANA HESAPLAMA ---
if st.button("STRATEJİK ANALİZİ BAŞLAT 🚀"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen dört dosyayı da yükleyin!")
    else:
        df_tr = pd.read_excel(tr_file); df_tr.columns = df_tr.columns.str.strip()
        df_hb = pd.read_excel(hb_file); df_hb.columns = df_hb.columns.str.strip()
        df_maliyet = pd.read_excel(maliyet_file); df_maliyet.columns = df_maliyet.columns.str.strip()
        df_kargo = pd.read_excel(kargo_file); df_kargo.columns = df_kargo.columns.str.strip()

        results = []

        # --- TRENDYOL ---
        for _, row in df_tr.iterrows():
            m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                           (df_maliyet['StokKodu'].astype(str) == str(row.get('Tedarikçi Stok Kodu'))) |
                           (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
            if not m.empty:
                alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                satis = to_float(row.get("Trendyol'da Satılacak Fiyat (KDV Dahil)", 0))
                kom_oran = to_float(row.get('Komisyon Oranı', 0))
                desi = to_float(row.get('Desi', 0))
                if desi <= 0: desi = to_float(m.iloc[0].get('Desi', 0))
                kargo_tl = kargo_hesapla(desi, df_kargo)
                kom_tl = satis * (kom_oran / 100)
                iade_risk_tl = kargo_tl * (iade_orani / 100)
                toplam_maliyet = alis + kom_tl + kargo_tl + tr_sabit + iade_risk_tl
                net_kar = satis - toplam_maliyet
                results.append({
                    "Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Desi": desi, "Satış Fiyatı": satis, "Alış Maliyeti": alis,
                    "Komisyon TL": round(kom_tl, 2), "Gidiş Kargo": round(kargo_tl, 2), "Sabit Gider": tr_sabit,
                    "İade Karşılığı (TL)": round(iade_risk_tl, 2), "TOPLAM MALİYET": round(toplam_maliyet, 2),
                    "NET KAR": round(net_kar, 2), "Marj %": round((net_kar/satis)*100, 2) if satis > 0 else 0,
                    "ROI %": round((net_kar/toplam_maliyet)*100, 2) if toplam_maliyet > 0 else 0
                })

        # --- HEPSİBURADA ---
        for _, row in df_hb.iterrows():
            m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                           (df_maliyet['StokKodu'].astype(str) == str(row.get('Satıcı Stok Kodu'))) |
                           (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
            if not m.empty:
                alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                satis = to_float(row.get('Fiyat', 0))
                kom_oran = to_float(row.get('Komisyon Oranı', 0))
                desi = to_float(m.iloc[0].get('Desi', 0))
                kargo_tl = kargo_hesapla(desi, df_kargo)
                kom_kdvli_tl = (satis * (kom_oran / 100)) * 1.20 
                tahsilat_tl = satis * hb_tahsilat_oran
                iade_risk_tl = (kargo_tl * 2) * (iade_orani / 100) 
                toplam_maliyet = alis + kom_kdvli_tl + tahsilat_tl + kargo_tl + hb_sabit + iade_risk_tl
                net_kar = satis - toplam_maliyet
                results.append({
                    "Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Desi": desi, "Satış Fiyatı": satis, "Alış Maliyeti": alis,
                    "Komisyon TL": round(kom_kdvli_tl, 2), "Tahsilat Bedeli (TL)": round(tahsilat_tl, 2),
                    "Gidiş Kargo": round(kargo_tl, 2), "Sabit Gider": hb_sabit, "İade Karşılığı (TL)": round(iade_risk_tl, 2),
                    "TOPLAM MALİYET": round(toplam_maliyet, 2), "NET KAR": rou
