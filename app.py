import streamlit as st
import pandas as pd
import io

# --- 1. SİSTEM VE GÜVENLİK AYARLARI ---
st.set_page_config(page_title="Pazaryeri ERP Kar Yönetimi", layout="wide")

# Kurumsal Tema (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .sidebar .sidebar-content { background-color: #1e3d59; color: white; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #d9534f; font-weight: bold; }
    .stDataFrame { border: 1px solid #dee2e6; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HESAP MOTORU (ASLA DOKUNULMADI - KIRMIZI ÇİZGİ) ---
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

# --- 3. VERİ HAFIZASI (ERP KERNEL) ---
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None

# --- 4. YAN MENÜ (ERP NAVIGASYON) ---
st.sidebar.title("💎 ERP Yönetim Paneli")
menu = st.sidebar.radio("DEPARTMANLAR", 
    ["📊 Dashboard", "📂 Veri Aktarım Merkezi", "📋 Kar Analiz Merkezi", "🎯 Strateji & Kampanya", "⚙️ Sistem Ayarları"])

# --- 5. SİSTEM AYARLARI ---
if 'settings' not in st.session_state:
    st.session_state.settings = {'tr_sabit': 15.0, 'hb_sabit': 15.0, 'hb_tahsilat': 0.008, 'iade_oran': 5.0}

if menu == "⚙️ Ayarlar":
    st.header("⚙️ Global Parametreler")
    st.info("Buradaki değişiklikler tüm hesaplamaları anlık olarak günceller.")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.settings['tr_sabit'] = st.number_input("Trendyol Sabit Gider", value=st.session_state.settings['tr_sabit'])
        st.session_state.settings['hb_sabit'] = st.number_input("HB Sabit Gider", value=st.session_state.settings['hb_sabit'])
    with c2:
        st.session_state.settings['hb_tahsilat'] = st.number_input("HB Tahsilat Oranı (%)", value=st.session_state.settings['hb_tahsilat']*100)/100
        st.session_state.settings['iade_oran'] = st.slider("Tahmini İade Oranı (%)", 0, 25, int(st.session_state.settings['iade_oran']))

# --- 6. VERİ AKTARIM MERKEZİ ---
elif menu == "📂 Veri Aktarım Merkezi":
    st.header("📂 Dosya Yükleme Paneli")
    col1, col2 = st.columns(2)
    with col1:
        tr_f = st.file_uploader("Trendyol Ürün Listesi", type=['xlsx'])
        m_f = st.file_uploader("Maliyet Listesi", type=['xlsx'])
    with col2:
        hb_f = st.file_uploader("Hepsiburada Ürün Listesi", type=['xlsx'])
        k_f = st.file_uploader("Kargo Fiyat Listesi", type=['xlsx'])
    
    if st.button("SİSTEMİ GÜNCELLE VE ANALİZ ET 🚀"):
        if tr_f and hb_f and m_f and k_f:
            df_tr = pd.read_excel(tr_f); df_hb = pd.read_excel(hb_f)
            df_m = pd.read_excel(m_f); df_k = pd.read_excel(k_f)
            for d in [df_tr, df_hb, df_m, df_k]: d.columns = d.columns.str.strip()
            
            res = []
            s = st.session_state.settings
            
            # --- HESAP MOTORU DÖNGÜSÜ ---
            # Trendyol
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
                    res.append({"Platform": "Trendyol", "Marka": r.get('Marka','-'), "Kod": r.get('Tedarikçi Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": to_float(r.get('Komisyon Oranı', 0)), "Komisyon TL": kom_tl, "Tahsilat Bedeli (TL)": 0.0, "Desi": desi, "Gidiş Kargo": kargo, "Sabit Gider": s['tr_sabit'], "İade Karşılığı (TL)": iade, "TOPLAM MALİYET": toplam_m, "NET KAR": satis - toplam_m, "Kar Marjı %": ((satis - toplam_m)/satis)*100 if satis > 0 else 0})

            # Hepsiburada
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
                    res.append({"Platform": "Hepsiburada", "Marka": r.get('Marka','-'), "Kod": r.get('Satıcı Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'), "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": kom_o, "Komisyon TL": kom_tl, "Tahsilat Bedeli (TL)": tahsilat, "Desi": desi, "Gidiş Kargo": kargo, "Sabit Gider": s['hb_sabit'], "İade Karşılığı (TL)": iade, "TOPLAM MALİYET": toplam_m, "NET KAR": satis - toplam_m, "Kar Marjı %": ((satis - toplam_m)/satis)*100 if satis > 0 else 0})
            
            st.session_state.processed_df = pd.DataFrame(res)
            st.success("✅ Veriler ERP hafızasına alındı!")

# --- 7. DASHBOARD ---
elif menu == "📊 Dashboard":
    st.header("📊 Finansal Durum Özeti")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Toplam Kar", f"{df['NET KAR'].sum():,.2f} TL")
        c2.metric("Toplam Ciro", f"{df['Satış Fiyatı'].sum():,.2f} TL")
        c3.metric("Ortalama Marj", f"%{df['Kar Marjı %'].mean():.2f}")
        c4.metric("Kritik Ürün Sayısı", len(df[df['Kar Marjı %'] < 10]))
        
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.write("### 🏢 Marka Bazlı Kar Dağılımı")
            st.bar_chart(df.groupby('Marka')['NET KAR'].sum())
        with col_g2:
            st.write("### 🌐 Platform Karlılık Kıyaslaması")
            st.bar_chart(df.groupby('Platform')['Kar Marjı %'].mean())
    else:
        st.warning("Hafızada veri bulunamadı. Lütfen Veri Aktarım Merkezi'ni kullanın.")

# --- 8. KAR ANALİZ MERKEZİ (KIRMIZI ÇİZGİ) ---
elif menu == "📋 Kar Analiz Merkezi":
    st.header("📋 Ürün Bazlı Kar/Zarar Detayları")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        # Sütun Sıralaması (SENİN KIRMIZI ÇİZGİN)
        cols = ["Platform", "Marka", "Kod", "Ürün", "Satış Fiyatı", "Alış Maliyeti", "Komisyon %", "Komisyon TL", "Tahsilat Bedeli (TL)", "Desi", "Gidiş Kargo", "Sabit Gider", "İade Karşılığı (TL)", "TOPLAM MALİYET", "NET KAR", "Kar Marjı %"]
        st.dataframe(df[cols].sort_values("NET KAR", ascending=False), use_container_width=True)
        
        output = io.BytesIO()
        df[cols].to_excel(output, index=False)
        st.download_button("📥 Analizi Excel Olarak İndir", output.getvalue(), "ERP_Kar_Raporu.xlsx")
    else:
        st.warning("Veri bulunamadı.")

# --- 9. STRATEJİ VE KAMPANYA ---
elif menu == "🎯 Strateji & Kampanya":
    st.header("🎯 Kampanya Simülatörü")
    if st.session_state.processed_df is not None:
        df_sim = st.session_state.processed_df.copy()
        indirim = st.slider("Kampanya İndirimi (%)", 0, 40, 0)
        df_sim['Yeni Satış'] = df_sim['Satış Fiyatı'] * (1 - indirim/100)
        df_sim['Yeni Net Kar'] = df_sim['Yeni Satış'] - df_sim['TOPLAM MALİYET']
        
        st.metric("Simülasyon Sonrası Toplam Kar", f"{df_sim['Yeni Net Kar'].sum():,.2f} TL")
        st.dataframe(df_sim[["Ürün", "Satış Fiyatı", "Yeni Satış", "NET KAR", "Yeni Net Kar"]], use_container_width=True)
