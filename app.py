import streamlit as st
import pandas as pd
import io
import re

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")
st.title("🚀 Pazaryeri Kar & Maliyet Analiz Sistemi")
st.markdown("Trendyol ve Hepsiburada verilerini maliyetlerinizle saniyeler içinde birleştirin.")

# --- YARDIMCI FONKSİYONLAR ---
def to_float(val):
    """Rakamları temizler ve sayıya çevirir (TL, boşluk, virgül temizliği)"""
    if pd.isna(val) or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Metin ise temizle
    res = str(val).replace('TL', '').replace('%', '').strip()
    # Türkçe formatı (1.250,50) -> İngilizce formatına (1250.50) çevir
    if ',' in res and '.' in res:
        res = res.replace('.', '').replace(',', '.')
    elif ',' in res:
        res = res.replace(',', '.')
    
    try:
        return float(res)
    except:
        return 0.0

def kargo_hesapla(desi, kargo_df):
    try:
        kargo_df.columns = kargo_df.columns.str.strip()
        desi_val = to_float(desi)
        if desi_val <= 30:
            return kargo_df.loc[kargo_df['DESİ'] >= desi_val, 'Fiyat'].iloc[0]
        else:
            return 447.06 + ((desi_val - 30) * 14.87)
    except:
        return 0.0

# --- DOSYA YÜKLEME ALANI ---
with st.sidebar:
    st.header("📂 Dosyaları Yükle")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi", type=['xlsx'])
    
    st.divider()
    sabit_gider = st.number_input("Platform Sabit Gider (TL)", value=15.0)
    hb_tahsilat = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100

# --- ANA HESAPLAMA MOTORU ---
if st.button("ANALİZİ BAŞLAT ✨"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen dört dosyayı da yükleyin!")
    else:
        # Excel'leri Oku
        df_tr = pd.read_excel(tr_file)
        df_hb = pd.read_excel(hb_file)
        df_maliyet = pd.read_excel(maliyet_file)
        df_kargo = pd.read_excel(kargo_file)
        
        # Başlık Temizliği
        for df in [df_tr, df_hb, df_maliyet, df_kargo]:
            df.columns = df.columns.str.strip()

        results = []
        errors = []

        # --- TRENDYOL İŞLEME ---
        for _, row in df_tr.iterrows():
            m = df_maliyet[(df_maliyet['Barkod'].astype(str) == str(row.get('Barkod'))) | 
                           (df_maliyet['StokKodu'].astype(str) == str(row.get('Tedarikçi Stok Kodu'))) |
                           (df_maliyet['Ürün Adı'].astype(str) == str(row.get('Ürün Adı')))]
            
            if not m.empty:
                alis = to_float(m.iloc[0].get('Alış Fiyatı', 0))
                satis = to_float(row.get("Trendyol'da Satılacak Fiyat (KDV Dahil)", 0))
                kom_oran = to_float(row.get('Komisyon Oranı', 0))
                desi = to_float(row.get('Desi', m.iloc[0].get('Desi', 0)))
                
                kargo_tl = kargo_hesapla(desi, df_kargo)
                kom_tl = satis * (kom_oran / 100)
                net_kar = satis - (alis + kom_tl + kargo_tl + sabit_gider)
                
                results.append({
                    "Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Maliyet": alis, "Kargo": kargo_tl, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Trendyol", "Kod": row.get('Tedarikçi Stok Kodu','-'), "Hata": "Eşleşmedi"})

        # --- HEPSİBURADA İŞLEME ---
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
                kom_kdvli = (satis * (kom_oran / 100)) * 1.20
                tahsilat_tl = satis * hb_tahsilat
                
                net_kar = satis - (alis + kom_kdvli + tahsilat_tl + kargo_tl + sabit_gider)
                results.append({
                    "Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Maliyet": alis, "Kargo": kargo_tl, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Hepsiburada", "Kod": row.get('Satıcı Stok Kodu','-'), "Hata": "Eşleşmedi"})

        # --- SONUÇLAR ---
        if results:
            final_df = pd.DataFrame(results)
            final_df["Kar Marjı %"] = (final_df["Net Kar"] / final_df["Satış"]) * 100
            st.success("Hesaplama Başarılı!")
            st.dataframe(final_df)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False)
            st.download_button("Excel İndir", output.getvalue(), "Rapor.xlsx")
