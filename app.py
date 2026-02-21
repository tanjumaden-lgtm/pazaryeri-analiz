import streamlit as st
import pandas as pd
import io

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(page_title="Pazaryeri ERP Kar Yönetimi", layout="wide")

# Kurumsal Stil
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .sidebar .sidebar-content { background-image: linear-gradient(#1e3d59,#1e3d59); color: white; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #d9534f; font-weight: bold; }
    .stDataFrame { border: 1px solid #dee2e6; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HESAP MOTORU FONKSİYONLARI (DOKUNULMAZLAR) ---
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
            return 447.06 + ((desi_val - 30) * 14.87)
    except: return 0.0

# --- 3. ERP KALICI HAFIZA SİSTEMİ (SESSION STATE) ---
if 'master_maliyet' not in st.session_state: st.session_state.master_maliyet = None
if 'master_kargo' not in st.session_state: st.session_state.master_kargo = None
if 'processed_df' not in st.session_state: st.session_state.processed_df = None
if 'settings' not in st.session_state:
    st.session_state.settings = {'tr_sabit': 15.0, 'hb_sabit': 15.0, 'hb_tahsilat': 0.008, 'iade_oran': 5.0}

# --- 4. YAN MENÜ SIRALAMASI ---
st.sidebar.title("💎 ERP Kar Yönetimi")
menu = st.sidebar.radio("DEPARTMANLAR", 
    ["📊 Dashboard", 
     "📂 Veri Aktarım Merkezi", 
     "📋 Kar Analiz Merkezi", 
     "📦 Envanter ve Maliyet", 
     "🚛 Lojistik ve Operasyon", 
     "🎯 Strateji & Kampanya", 
     "⚙️ Sistem Ayarları"])

# --- 5. ENVANTER VE MALİYET (ANA VERİ GİRİŞİ) ---
if menu == "📦 Envanter ve Maliyet":
    st.header("📦 Envanter ve Maliyet Yönetimi")
    st.write("Ürün alış fiyatlarınızı ve ana listenizi buradan sisteme kaydedin.")
    m_f = st.file_uploader("Maliyet Listesini Yükle (Master Data)", type=['xlsx'])
    if m_f:
        df_m = pd.read_excel(m_f)
        df_m.columns = df_m.columns.str.strip()
        st.session_state.master_maliyet = df_m
        st.success("✅ Maliyet Listesi Ana Veri Olarak Kaydedildi!")
    
    if st.session_state.master_maliyet is not None:
        st.subheader("Sistemdeki Mevcut Maliyet Verileri")
        st.dataframe(st.session_state.master_maliyet.head(10))

# --- 6. LOJİSTİK VE OPERASYON (ANA VERİ GİRİŞİ) ---
elif menu == "🚛 Lojistik ve Operasyon":
    st.header("🚛 Lojistik ve Operasyon Yönetimi")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("Kargo Fiyat Listesi")
        k_f = st.file_uploader("Güncel Kargo Listesini Yükle", type=['xlsx'])
        if k_f:
            df_k = pd.read_excel(k_f)
            df_k.columns = df_k.columns.str.strip()
            st.session_state.master_kargo = df_k
            st.success("✅ Kargo Tablosu Kaydedildi!")
    with col_l2:
        st.subheader("İade Risk Ayarı")
        st.session_state.settings['iade_oran'] = st.slider("Tahmini İade Oranı (%)", 0, 25, int(st.session_state.settings['iade_oran']))

# --- 7. VERİ AKTARIM MERKEZİ (GÜNLÜK RAPORLAR) ---
elif menu == "📂 Veri Aktarım Merkezi":
    st.header("📂 Günlük Satış Aktarımı")
    if st.session_state.master_maliyet is None or st.session_state.master_kargo is None:
        st.error("⚠️ Önce 'Envanter' ve 'Lojistik' menülerinden ana verileri yüklemelisiniz!")
    else:
        st.success("✅ Master Data Hazır. Sadece satış raporlarını yükleyin.")
        col1, col2 = st.columns(2)
        with col1: tr_f = st.file_uploader("Trendyol Satış Raporu", type=['xlsx'])
        with col2: hb_f = st.file_uploader("Hepsiburada Satış Raporu", type=['xlsx'])
        
        if st.button("ANALİZİ ÇALIŞTIR 🚀"):
            if tr_f and hb_f:
                df_tr = pd.read_excel(tr_f); df_hb = pd.read_excel(hb_f)
                df_m = st.session_state.master_maliyet; df_k = st.session_state.master_kargo
                for d in [df_tr, df_hb]: d.columns = d.columns.str.strip()
                
                res = []
                s = st.session_state.settings
                
                # TRENDYOL HESAPLAMA
                for _, r in df_tr.iterrows():
                    m_match = df_m[(df_m['Barkod'].astype(str) == str(r.get('Barkod'))) | (df_m['StokKodu'].astype(str) == str(r.get('Tedarikçi Stok Kodu'))) | (df_m['Ürün Adı'].astype(str) == str(r.get('Ürün Adı')))]
                    if not m_match.empty:
                        alis = to_float(m_match.iloc[0].get('Alış Fiyatı', 0))
                        satis = to_float(r.get("Trendyol'da Satılacak Fiyat (KDV Dahil)", 0))
                        desi = to_float(r.get('Desi', m_match.iloc[0].get('Desi', 0)))
                        kargo = kargo_hesapla(desi, df_k)
                        kom_tl = satis * (to_float(r.get('Komisyon Oranı', 0)) / 100)
                        iade = kargo * (s['iade_oran'] / 100)
                        toplam_m = alis + kom_tl + kargo + s['tr_sabit'] + iade
                        res.append({"Platform": "Trendyol", "Marka": r.get('Marka','-'), "Kod": r.get('Tedarikçi Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(to_float(r.get('Komisyon Oranı', 0)), 2), "Komisyon TL": round(kom_tl, 2), "Tahsilat Bedeli (TL)": 0.0, "Desi": desi, "Gidiş Kargo": round(kargo, 2), "Sabit Gider": s['tr_sabit'], "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(toplam_m, 2), "NET KAR": round(satis - toplam_m, 2), "Kar Marjı %": round(((satis - toplam_m)/satis)*100, 2) if satis > 0 else 0})

                # HEPSİBURADA HESAPLAMA
                for _, r in df_hb.iterrows():
                    m_match = df_m[(df_m['Barkod'].astype(str) == str(r.get('Barkod'))) | (df_m['StokKodu'].astype(str) == str(r.get('Satıcı Stok Kodu'))) | (df_m['Ürün Adı'].astype(str) == str(r.get('Ürün Adı')))]
                    if not m_match.empty:
                        alis = to_float(m_match.iloc[0].get('Alış Fiyatı', 0))
                        satis = to_float(r.get('Fiyat', 0))
                        kom_o = to_float(r.get('Komisyon Oranı', 0)) * 1.20
                        kom_tl = satis * (kom_o / 100)
                        tahsilat = satis * s['hb_tahsilat']
                        desi = to_float(m_match.iloc[0].get('Desi', 0))
                        kargo = kargo_hesapla(desi, df_k)
                        iade = (kargo * 2) * (s['iade_oran'] / 100)
                        toplam_m = alis + kom_tl + tahsilat + kargo + s['hb_sabit'] + iade
                        res.append({"Platform": "Hepsiburada", "Marka": r.get('Marka','-'), "Kod": r.get('Satıcı Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(kom_o, 2), "Komisyon TL": round(kom_tl, 2), "Tahsilat Bedeli (TL)": round(tahsilat, 2), "Desi": desi, "Gidiş Kargo": round(kargo, 2), "Sabit Gider": s['hb_sabit'], "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(toplam_m, 2), "NET KAR": round(satis - toplam_m, 2), "Kar Marjı %": round(((satis - toplam_m)/satis)*100, 2) if satis > 0 else 0})
                
                st.session_state.processed_df = pd.DataFrame(res)
                st.success("🚀 Analiz Bitti! Dashboard'a gidebilirsiniz.")

# --- 8. DASHBOARD ---
elif menu == "📊 Dashboard":
    st.header("📊 Finansal Durum")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Kar", f"{df['NET KAR'].sum():,.2f} TL")
        c2.metric("Toplam Ciro", f"{df['Satış Fiyatı'].sum():,.2f} TL")
        c3.metric("Kritik Ürün", len(df[df['Kar Marjı %'] < 10]))
        st.bar_chart(df.groupby('Marka')['NET KAR'].sum())
    else: st.warning("Veri Merkezi'nden analiz yapın.")

# --- 9. KAR ANALİZ MERKEZİ ---
elif menu == "📋 Kar Analiz Merkezi":
    st.header("📋 Detaylı Kar Listesi")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        cols = ["Platform", "Marka", "Kod", "Ürün", "Satış Fiyatı", "Alış Maliyeti", "Komisyon %", "Komisyon TL", "Tahsilat Bedeli (TL)", "Desi", "Gidiş Kargo", "Sabit Gider", "İade Karşılığı (TL)", "TOPLAM MALİYET", "NET KAR", "Kar Marjı %"]
        st.dataframe(df[cols].sort_values("NET KAR", ascending=False), use_container_width=True)
    else: st.warning("Veri bulunamadı.")

# --- 10. DİĞER MENÜLER (TASLAK) ---
elif menu == "🎯 Strateji & Kampanya":
    st.header("🎯 Kampanya Simülatörü")
    st.write("Bu bölüm aktif veri üzerinden simülasyon yapar.")

elif menu == "⚙️ Sistem Ayarları":
    st.header("⚙️ Genel Ayarlar")
    st.session_state.settings['tr_sabit'] = st.number_input("Trendyol Sabit", value=st.session_state.settings['tr_sabit'])
    st.session_state.settings['hb_sabit'] = st.number_input("HB Sabit", value=st.session_state.settings['hb_sabit'])
