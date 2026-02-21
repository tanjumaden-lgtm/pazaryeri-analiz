import streamlit as st
import pandas as pd
import io

# --- 1. SİSTEM AYARLARI VE TASARIM ---
st.set_page_config(page_title="Pazaryeri ERP Kar Yönetimi", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .main-card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1e3d59; font-weight: bold; }
    .sidebar .sidebar-content { background-color: #1e3d59; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. HESAP MOTORU (ASLA DEĞİŞMEYEN ANA MATEMATİK) ---
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

# --- 3. VERİ SAKLAMA (SESSION STATE) ---
if 'final_data' not in st.session_state:
    st.session_state.final_data = None

# --- 4. YAN MENÜ (NAVIGATION) ---
st.sidebar.title("💎 Kar Yönetim Paneli")
menu = st.sidebar.radio("MENÜ", ["📊 Dashboard", "📂 Veri Merkezi", "📋 Ürün Analizi", "🎯 Reklam & Kampanya", "⚙️ Ayarlar"])

# --- 5. AYARLAR SAYFASI (HAFIZADA TUTULUR) ---
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'tr_sabit': 15.0, 'hb_sabit': 15.0, 'hb_tahsilat': 0.008, 'iade_oran': 5.0, 'reklam_oran': 10.0
    }

if menu == "⚙️ Ayarlar":
    st.header("⚙️ Sistem Ayarları")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.settings['tr_sabit'] = st.number_input("Trendyol Sabit Gider (TL)", value=st.session_state.settings['tr_sabit'])
        st.session_state.settings['hb_sabit'] = st.number_input("HB Sabit Gider (TL)", value=st.session_state.settings['hb_sabit'])
    with col2:
        st.session_state.settings['hb_tahsilat'] = st.number_input("HB Tahsilat Bedeli (%)", value=st.session_state.settings['hb_tahsilat']*100) / 100
        st.session_state.settings['iade_oran'] = st.slider("İade Oranı (%)", 0, 25, int(st.session_state.settings['iade_oran']))
    st.success("Ayarlar otomatik olarak kaydedildi ve tüm hesaplamalara yansıtıldı.")

# --- 6. VERİ MERKEZİ (YÜKLEME VE ANALİZ) ---
elif menu == "📂 Veri Merkezi":
    st.header("📂 Veri Giriş Merkezi")
    st.info("Lütfen güncel pazaryeri ve maliyet Excel dosyalarınızı buraya yükleyin.")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
        maliyet_file = st.file_uploader("3. Maliyet Listesi", type=['xlsx'])
    with col_up2:
        hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
        kargo_file = st.file_uploader("4. Kargo Fiyat Listesi", type=['xlsx'])

    if st.button("TÜM VERİLERİ HARMANLA VE ANALİZ ET 🚀"):
        if not (tr_file and hb_file and maliyet_file and kargo_file):
            st.error("Eksik dosya var!")
        else:
            # Okuma ve Analiz Süreci
            df_tr = pd.read_excel(tr_file); df_tr.columns = df_tr.columns.str.strip()
            df_hb = pd.read_excel(hb_file); df_hb.columns = df_hb.columns.str.strip()
            df_maliyet = pd.read_excel(maliyet_file); df_maliyet.columns = df_maliyet.columns.str.strip()
            df_kargo = pd.read_excel(kargo_file); df_kargo.columns = df_kargo.columns.str.strip()

            results = []
            s = st.session_state.settings

            # TRENDYOL İŞLEME
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
                    kargo = kargo_hesapla(desi, df_kargo)
                    kom_tl = satis * (kom_oran / 100)
                    iade = kargo * (s['iade_oran'] / 100)
                    top_maliyet = alis + kom_tl + kargo + s['tr_sabit'] + iade
                    
                    results.append({
                        "Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'), "Ürün": row.get('Ürün Adı','-'),
                        "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(kom_oran, 2), "Komisyon TL": round(kom_tl, 2),
                        "Tahsilat Bedeli (TL)": 0.0, "Desi": desi, "Gidiş Kargo": round(kargo, 2), "Sabit Gider": s['tr_sabit'],
                        "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(top_maliyet, 2), "NET KAR": round(satis - top_maliyet, 2), "Kar Marjı %": round(((satis - top_maliyet)/satis)*100, 2) if satis > 0 else 0
                    })

            # HB İŞLEME
            for _, row in df_hb.iterrows():
                m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                               (df_maliyet['StokKodu'].astype(str) == str(row.get('Satıcı Stok Kodu'))) |
                               (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
                if not m.empty:
                    alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                    satis = to_float(row.get('Fiyat', 0))
                    kom_oran = to_float(row.get('Komisyon Oranı', 0)) * 1.20
                    kom_tl = satis * (kom_oran / 100)
                    tahsilat = satis * s['hb_tahsilat']
                    desi = to_float(m.iloc[0].get('Desi', 0))
                    kargo = kargo_hesapla(desi, df_kargo)
                    iade = (kargo * 2) * (s['iade_oran'] / 100)
                    top_maliyet = alis + kom_tl + tahsilat + kargo + s['hb_sabit'] + iade
                    
                    results.append({
                        "Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'), "Ürün": row.get('Ürün Adı','-'),
                        "Satış Fiyatı": satis, "Alış Maliyeti": alis, "Komisyon %": round(kom_oran, 2), "Komisyon TL": round(kom_tl, 2),
                        "Tahsilat Bedeli (TL)": round(tahsilat, 2), "Desi": desi, "Gidiş Kargo": round(kargo, 2), "Sabit Gider": s['hb_sabit'],
                        "İade Karşılığı (TL)": round(iade, 2), "TOPLAM MALİYET": round(top_maliyet, 2), "NET KAR": round(satis - top_maliyet, 2), "Kar Marjı %": round(((satis - top_maliyet)/satis)*100, 2) if satis > 0 else 0
                    })
            
            st.session_state.final_data = pd.DataFrame(results)
            st.success("Analiz bitti! Şimdi Dashboard veya Ürün Analiz menüsüne gidebilirsin.")

# --- 7. DASHBOARD (GRAFİKLER) ---
elif menu == "📊 Dashboard":
    st.header("📊 Yönetici Dashboard")
    if st.session_state.final_data is None:
        st.warning("Henüz veri yüklenmedi. Lütfen 'Veri Merkezi' menüsüne git.")
    else:
        df = st.session_state.final_data
        m1, m2, m3 = st.columns(3)
        m1.metric("Toplam Kar", f"{df['NET KAR'].sum():,.2f} TL")
        m2.metric("Genel Ciro", f"{df['Satış Fiyatı'].sum():,.2f} TL")
        m3.metric("Ortalama Marj", f"%{df['Kar Marjı %'].mean():.2f}")
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("### Marka Bazlı Net Kar")
            st.bar_chart(df.groupby('Marka')['NET KAR'].sum())
        with c2:
            st.write("### Platform Kar Dağılımı")
            st.pie_chart(df.groupby('Platform')['NET KAR'].sum())

# --- 8. ÜRÜN ANALİZİ (KIRMIZI ÇİZGİ TABLO) ---
elif menu == "📋 Ürün Analizi":
    st.header("📋 Detaylı Ürün Kar Listesi")
    if st.session_state.final_data is None:
        st.warning("Veri bulunamadı. Önce dosyaları yükle.")
    else:
        df = st.session_state.final_data
        # SIRALAMA VE GÖRÜNÜM (TAM İSTEDİĞİN GİBİ)
        cols = ["Platform", "Marka", "Kod", "Ürün", "Satış Fiyatı", "Alış Maliyeti", "Komisyon %", "Komisyon TL", "Tahsilat Bedeli (TL)", "Desi", "Gidiş Kargo", "Sabit Gider", "İade Karşılığı (TL)", "TOPLAM MALİYET", "NET KAR", "Kar Marjı %"]
        st.dataframe(df[cols].sort_values("NET KAR", ascending=False), use_container_width=True)
        
        output = io.BytesIO()
        df[cols].to_excel(output, index=False)
        st.download_button("📤 Raporu Excel Olarak İndir", output.getvalue(), "Kar_Raporu.xlsx")

# --- 9. REKLAM & KAMPANYA SİHİRBAZI ---
elif menu == "🎯 Reklam & Kampanya":
    st.header("🎯 Reklam ve Kampanya Sihirbazı")
    if st.session_state.final_data is None:
        st.warning("Veri yüklenmedi.")
    else:
        st.write("Bu bölümde genel reklam giderlerini ve kampanya indirimlerini test edebilirsin.")
        sim_acos = st.slider("Hedef Reklam Gideri (ACOS %)", 0, 30, int(st.session_state.settings['reklam_oran']))
        sim_indirim = st.slider("Planlanan Kampanya İndirimi (%)", 0, 50, 0)
        
        df = st.session_state.final_data.copy()
        # Simülasyon Hesaplama
        df['Yeni Satış'] = df['Satış Fiyatı'] * (1 - sim_indirim/100)
        df['Reklam Gideri'] = df['Yeni Satış'] * (sim_acos/100)
        df['Yeni Net Kar'] = df['Yeni Satış'] - df['TOPLAM MALİYET'] - df['Reklam Gideri']
        
        st.metric("Simülasyon Sonrası Toplam Kar", f"{df['Yeni Net Kar'].sum():,.2f} TL")
        st.dataframe(df[["Ürün", "Satış Fiyatı", "Yeni Satış", "Reklam Gideri", "Yeni Net Kar"]], use_container_width=True)
