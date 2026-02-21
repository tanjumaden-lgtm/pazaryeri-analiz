import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")
st.title("📊 Pazaryeri Strateji & Kar Yönetim Merkezi")

# --- YARDIMCI FONKSİYONLAR ---
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

# --- YÜKLEME ALANI (SOL PANEL) ---
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

# --- ANALİZ MOTORU ---
if st.button("STRATEJİK ANALİZİ BAŞLAT 🚀"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen tüm dosyaları yükleyin!")
    else:
        df_tr = pd.read_excel(tr_file); df_tr.columns = df_tr.columns.str.strip()
        df_hb = pd.read_excel(hb_file); df_hb.columns = df_hb.columns.str.strip()
        df_maliyet = pd.read_excel(maliyet_file); df_maliyet.columns = df_maliyet.columns.str.strip()
        df_kargo = pd.read_excel(kargo_file); df_kargo.columns = df_kargo.columns.str.strip()

        results = []

        # --- HESAPLAMA DÖNGÜSÜ ---
        # (Önceki kar hesaplama mantığın korundu, sadece veri topluyoruz)
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
                toplam_maliyet = alis + kom_tl + kargo + tr_sabit + iade_risk
                net_kar = satis - toplam_maliyet
                results.append({"Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'), "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Net Kar": net_kar, "Marj %": (net_kar/satis)*100 if satis>0 else 0, "Maliyet": toplam_maliyet})

        for _, row in df_hb.iterrows():
            m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                           (df_maliyet['StokKodu'].astype(str) == str(row.get('Satıcı Stok Kodu'))) |
                           (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
            if not m.empty:
                alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                satis = to_float(row.get('Fiyat', 0))
                kom_ham_oran = to_float(row.get('Komisyon Oranı', 0))
                kom_toplam_tl = satis * (kom_ham_oran * 1.20 / 100)
                desi = to_float(m.iloc[0].get('Desi', 0))
                kargo = kargo_hesapla(desi, df_kargo)
                tahsilat = satis * hb_tahsilat_oran
                iade_risk = (kargo * 2) * (iade_orani / 100)
                toplam_maliyet = alis + kom_toplam_tl + tahsilat + kargo + hb_sabit + iade_risk
                net_kar = satis - toplam_maliyet
                results.append({"Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'), "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Net Kar": net_kar, "Marj %": (net_kar/satis)*100 if satis>0 else 0, "Maliyet": toplam_maliyet})

        if results:
            df = pd.DataFrame(results)
            
            # --- 1. ÜST METRİKLER ---
            st.subheader("📌 Genel Performans Özeti")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Toplam Satış Hacmi", f"{df['Satış'].sum():,.0f} TL")
            m2.metric("Toplam Net Kar", f"{df['Net Kar'].sum():,.0f} TL")
            m3.metric("Ortalama Marj", f"%{df['Marj %'].mean():.2f}")
            m4.metric("Kritik Ürün Sayısı (%10 Altı)", len(df[df['Marj %'] < 10]))

            st.divider()

            # --- 2. GÖRSEL ANALİZ ---
            col1, col2 = st.columns(2)
            with col1:
                st.write("### 🏢 Marka Bazlı Kar Dağılımı")
                marka_kar = df.groupby('Marka')['Net Kar'].sum()
                st.bar_chart(marka_kar)
            with col2:
                st.write("### 🌐 Platform Bazlı Kar Marjı")
                plat_marj = df.groupby('Platform')['Marj %'].mean()
                st.bar_chart(plat_marj)

            st.divider()

            # --- 3. KRİTİK ÜRÜN UYARISI ---
            st.subheader("⚠️ Acil Müdahale Gereken Ürünler")
            st.write("Kar marjı %10'un altında olan ve karlılığı tehlikede olan ürünler:")
            kritik_df = df[df['Marj %'] < 10].sort_values('Marj %')
            st.dataframe(kritik_df, use_container_width=True)

            st.divider()

            # --- 4. TÜM VERİ TABLOSU ---
            st.subheader("📝 Tüm Ürün Analiz Detayları")
            st.dataframe(df.sort_values('Net Kar', ascending=False), use_container_width=True)

            # Excel İndir
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button("📥 Tam Raporu Excel İndir", output.getvalue(), "Stratejik_Kar_Analiz.xlsx")
