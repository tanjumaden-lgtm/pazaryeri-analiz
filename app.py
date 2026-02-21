import streamlit as st
import pandas as pd
import io

# --- 1. SİSTEM AYARLARI ---
st.set_page_config(page_title="Pazaryeri ERP Kar Yönetimi", layout="wide")

# Kurumsal Stil
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .sidebar .sidebar-content { background-color: #1e3d59; color: white; }
    div[data-testid="stMetricValue"] { font-size: 26px; color: #d9534f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HESAP MOTORU (KIRMIZI ÇİZGİ) ---
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

# --- 3. ERP HAFIZA YÖNETİMİ ---
if 'processed_df' not in st.session_state: st.session_state.processed_df = None
if 'kargo_df' not in st.session_state: st.session_state.kargo_df = None
if 'settings' not in st.session_state:
    st.session_state.settings = {'tr_sabit': 15.0, 'hb_sabit': 15.0, 'hb_tahsilat': 0.008, 'iade_oran': 5.0}

# --- 4. DEPARTMANLAR (MENÜ SIRALAMASI) ---
st.sidebar.title("💎 ERP Yönetim Paneli")
menu = st.sidebar.radio("DEPARTMANLAR", 
    ["📊 Dashboard", 
     "📂 Veri Aktarım Merkezi", 
     "📋 Kar Analiz Merkezi", 
     "🚛 Lojistik ve Operasyon", 
     "🎯 Strateji & Kampanya", 
     "⚙️ Sistem Ayarları"])

# --- 5. DASHBOARD ---
if menu == "📊 Dashboard":
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
        st.warning("Lütfen 'Veri Aktarım Merkezi'ne giderek raporları yükleyin.")

# --- 6. VERI AKTARIM MERKEZI ---
elif menu == "📂 Veri Aktarım Merkezi":
    st.header("📂 Dosya Yükleme Kapısı")
    st.info("Pazaryeri ve Maliyet dosyalarını buraya bırakın.")
    
    col1, col2 = st.columns(2)
    with col1:
        tr_f = st.file_uploader("Trendyol Ürün Listesi", type=['xlsx'])
        m_f = st.file_uploader("Maliyet Listesi", type=['xlsx'])
    with col2:
        hb_f = st.file_uploader("Hepsiburada Ürün Listesi", type=['xlsx'])
        k_f = st.file_uploader("Kargo Fiyat Listesi", type=['xlsx']) # Şimdilik burada kalabilir
    
    if st.button("ANALİZİ ÇALIŞTIR 🚀"):
        if tr_f and hb_f and m_f and k_f:
            df_tr = pd.read_excel(tr_f); df_hb = pd.read_excel(hb_f)
            df_m = pd.read_excel(m_f); df_k = pd.read_excel(k_f)
            for d in [df_tr, df_hb, df_m, df_k]: d.columns = d.columns.str.strip()
            
            res = []
            s = st.session_state.settings
            
            # --- TRENDYOL HESAPLAMA ---
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
                    res.append({
                        "Platform": "Trendyol", "Marka": r.get('Marka','-'), "Kod": r.get('Tedarikçi Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'),
                        "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(to_float(r.get('Komisyon Oranı', 0)), 2),
                        "Komisyon TL": round(kom_tl, 2), "Tahsilat Bedeli (TL)": 0.0, "Desi": desi, "Gidiş Kargo": round(kargo, 2),
                        "Sabit Gider": s['tr_sabit'], "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(toplam_m, 2),
                        "NET KAR": round(satis - toplam_m, 2), "Kar Marjı %": round(((satis - toplam_m)/satis)*100, 2) if satis > 0 else 0
                    })

            # --- HEPSIBURADA HESAPLAMA ---
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
                    res.append({
                        "Platform": "Hepsiburada", "Marka": r.get('Marka','-'), "Kod": r.get('Satıcı Stok Kodu','-'), "Ürün": r.get('Ürün Adı','-'),
                        "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(kom_o, 2),
                        "Komisyon TL": round(kom_tl, 2), "Tahsilat Bedeli (TL)": round(tahsilat, 2), "Desi": desi, "Gidiş Kargo": round(kargo, 2),
                        "Sabit Gider": s['hb_sabit'], "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(toplam_m, 2),
                        "NET KAR": round(satis - toplam_m, 2), "Kar Marjı %": round(((satis - toplam_m)/satis)*100, 2) if satis > 0 else 0
                    })
            
            st.session_state.processed_df = pd.DataFrame(res)
            st.success("✅ Tüm veriler harmanlandı ve ERP hafızasına alındı!")

# --- 7. KAR ANALIZ MERKEZI ---
elif menu == "📋 Kar Analiz Merkezi":
    st.header("📋 Ürün Kar/Zarar Detayları")
    if st.session_state.processed_df is not None:
        df = st.session_state.processed_df
        cols = ["Platform", "Marka", "Kod", "Ürün", "Satış Fiyatı", "Alış Maliyeti", "Komisyon %", "Komisyon TL", "Tahsilat Bedeli (TL)", "Desi", "Gidiş Kargo", "Sabit Gider", "İade Karşılığı (TL)", "TOPLAM MALİYET", "NET KAR", "Kar Marjı %"]
        st.dataframe(df[cols].sort_values("NET KAR", ascending=False), use_container_width=True)
        
        output = io.BytesIO()
        df[cols].to_excel(output, index=False)
        st.download_button("📥 Excel Raporunu İndir", output.getvalue(), "ERP_Kar_Detay.xlsx")
    else:
        st.warning("Henüz analiz yapılmadı.")

# --- 8. LOJISTIK VE OPERASYON ---
elif menu == "🚛 Lojistik ve Operasyon":
    st.header("🚛 Lojistik ve İade Yönetimi")
    st.info("Bu bölümde kargo maliyetlerinizi ve iade risklerinizi yönetirsiniz.")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.subheader("🔄 İade Risk Parametresi")
        st.session_state.settings['iade_oran'] = st.slider("Tahmini İade Oranı (%)", 0, 25, int(st.session_state.settings['iade_oran']))
        st.write(f"Şu anki iade payı: %{st.session_state.settings['iade_oran']}")
    with col_l2:
        st.subheader("📦 Kargo ve Desi")
        st.write("Kargo fiyat listenizi 'Veri Aktarım Merkezi'nden güncelleyebilirsiniz.")
        # İleride kargo listesini burada kalıcı hale getirebiliriz.

# --- 9. STRATEJI VE KAMPANYA ---
elif menu == "🎯 Strateji & Kampanya":
    st.header("🎯 Kampanya Simülatörü")
    if st.session_state.processed_df is not None:
        df_sim = st.session_state.processed_df.copy()
        indirim = st.slider("Kampanya İndirim Simülasyonu (%)", 0, 40, 0)
        df_sim['Yeni Satış'] = df_sim['Satış Fiyatı'] * (1 - indirim/100)
        df_sim['Yeni Net Kar'] = df_sim['Yeni Satış'] - df_sim['TOPLAM MALİYET']
        
        st.metric("Simülasyon Sonrası Toplam Tahmini Kar", f"{df_sim['Yeni Net Kar'].sum():,.2f} TL")
        st.dataframe(df_sim[["Ürün", "Satış Fiyatı", "Yeni Satış", "NET KAR", "Yeni Net Kar"]], use_container_width=True)
    else:
        st.warning("Önce veri yüklemelisiniz.")

# --- 10. SISTEM AYARLARI ---
elif menu == "⚙️ Sistem Ayarları":
    st.header("⚙️ Sistem Ayarları")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.settings['tr_sabit'] = st.number_input("Trendyol Platform Gideri", value=st.session_state.settings['tr_sabit'])
    with c2:
        st.session_state.settings['hb_sabit'] = st.number_input("HB Platform Gideri", value=st.session_state.settings['hb_sabit'])
        st.session_state.settings['hb_tahsilat'] = st.number_input("HB Tahsilat Oranı (%)", value=st.session_state.settings['hb_tahsilat']*100)/100
