import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")

# --- MODERN TASARIM (Görsellik İçin Sabit Tutuldu) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Pazaryeri Strateji & Kar Yönetim Merkezi")

# --- 1. HESAP MOTORU FONKSİYONLARI ---
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

# --- 2. GİRİŞ PANELİ (SIDEBAR) ---
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

# --- 3. ANA ANALİZ VE TABLO OLUŞTURMA ---
if st.button("STRATEJİK ANALİZİ BAŞLAT 🚀"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen dört dosyayı da yükleyin!")
    else:
        df_tr = pd.read_excel(tr_file); df_tr.columns = df_tr.columns.str.strip()
        df_hb = pd.read_excel(hb_file); df_hb.columns = df_hb.columns.str.strip()
        df_maliyet = pd.read_excel(maliyet_file); df_maliyet.columns = df_maliyet.columns.str.strip()
        df_kargo = pd.read_excel(kargo_file); df_kargo.columns = df_kargo.columns.str.strip()

        results = []

        # --- TRENDYOL DÖNGÜSÜ ---
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
                iade_risk = kargo * (iade_orani / 100)
                toplam_maliyet = alis + kom_tl + 0.0 + kargo + tr_sabit + iade_risk
                net_kar = satis - toplam_maliyet
                
                # SENİN TABLO SIRALAMAN (Tam Olarak Görseldeki Gibi)
                results.append({
                    "Platform": "Trendyol",
                    "Marka": row.get('Marka','-'),
                    "Kod": row.get('Tedarikçi Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'),
                    "Satış Fiyatı": satis,
                    "Alış Maliyeti": alis,
                    "Komisyon %": round(kom_oran, 2),
                    "Komisyon TL": round(kom_tl, 2),
                    "Tahsilat Bedeli (TL)": 0.0,
                    "Desi": desi,
                    "Gidiş Kargo": round(kargo, 2),
                    "Sabit Gider": tr_sabit,
                    "İade Karşılığı (TL)": round(iade_risk, 2),
                    "TOPLAM MALİYET": round(toplam_maliyet, 2),
                    "NET KAR": round(net_kar, 2),
                    "Kar Marjı %": round((net_kar/satis)*100, 2) if satis > 0 else 0
                })

        # --- HEPSİBURADA DÖNGÜSÜ ---
        for _, row in df_hb.iterrows():
            m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                           (df_maliyet['StokKodu'].astype(str) == str(row.get('Satıcı Stok Kodu'))) |
                           (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
            if not m.empty:
                alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                satis = to_float(row.get('Fiyat', 0))
                kom_ham_oran = to_float(row.get('Komisyon Oranı', 0))
                kom_kdvli_oran = kom_ham_oran * 1.20 # HB %20 KDV Kuralı
                kom_tl = satis * (kom_kdvli_oran / 100)
                tahsilat = satis * hb_tahsilat_oran
                desi = to_float(m.iloc[0].get('Desi', 0))
                kargo = kargo_hesapla(desi, df_kargo)
                iade_risk = (kargo * 2) * (iade_orani / 100) # HB 3. Kargo Kuralı
                toplam_maliyet = alis + kom_tl + tahsilat + kargo + hb_sabit + iade_risk
                net_kar = satis - toplam_maliyet
                
                # SENİN TABLO SIRALAMAN (Tam Olarak Görseldeki Gibi)
                results.append({
                    "Platform": "Hepsiburada",
                    "Marka": row.get('Marka','-'),
                    "Kod": row.get('Satıcı Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'),
                    "Satış Fiyatı": satis,
                    "Alış Maliyeti": alis,
                    "Komisyon %": round(kom_kdvli_oran, 2),
                    "Komisyon TL": round(kom_tl, 2),
                    "Tahsilat Bedeli (TL)": round(tahsilat, 2),
                    "Desi": desi,
                    "Gidiş Kargo": round(kargo, 2),
                    "Sabit Gider": hb_sabit,
                    "İade Karşılığı (TL)": round(iade_risk, 2),
                    "TOPLAM MALİYET": round(toplam_maliyet, 2),
                    "NET KAR": round(net_kar, 2),
                    "Kar Marjı %": round((net_kar/satis)*100, 2) if satis > 0 else 0
                })

        # --- 4. GÖRSELLEŞTİRME ---
        if results:
            df = pd.DataFrame(results)
            st.success("✅ Analiz Tamamlandı!")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Kar", f"{df['NET KAR'].sum():,.2f} TL")
            m2.metric("Ortalama Marj", f"%{df['Kar Marjı %'].mean():.2f}")
            m3.metric("Kritik Ürün", len(df[df['Kar Marjı %'] < 10]))
            m4.metric("Toplam Satış", f"{df['Satış Fiyatı'].sum():,.0f} TL")

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Marka Kar Dağılımı")
                st.bar_chart(df.groupby('Marka')['NET KAR'].sum())
            with col2:
                st.write("### Platform Marj Kıyaslama")
                st.bar_chart(df.groupby('Platform')['Kar Marjı %'].mean())

            # ANA TABLO - SENİN İSTEDİĞİN SÜTUNLAR VE SIRALAMA
            st.divider()
            st.subheader("📋 Detaylı Ürün Analiz Tablosu")
            st.dataframe(df.sort_values('NET KAR', ascending=False), use_container_width=True)

            # EXCEL İNDİRME
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button("📥 Raporu Excel Olarak İndir", output.getvalue(), "Pazaryeri_Analiz.xlsx")
