import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")
st.title("🚀 Pazaryeri Kar & Maliyet Analiz Sistemi")

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
        if desi_val <= 30:
            # En yakın üst desiyi bul
            return kargo_df.loc[kargo_df['DESİ'] >= desi_val, 'Fiyat'].iloc[0]
        else:
            return 447.06 + ((desi_val - 30) * 14.87)
    except:
        return 0.0

# --- YÜKLEME ALANI ---
with st.sidebar:
    st.header("📂 Dosyaları Yükle")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi", type=['xlsx'])
    
    st.divider()
    sabit_gider_val = st.number_input("Platform Sabit Gider (TL)", value=15.0)
    hb_tahsilat_oran = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100

# --- HESAPLAMA ---
if st.button("ANALİZİ BAŞLAT ✨"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen tüm dosyaları yükleyin!")
    else:
        df_tr = pd.read_excel(tr_file)
        df_hb = pd.read_excel(hb_file)
        df_maliyet = pd.read_excel(maliyet_file)
        df_kargo = pd.read_excel(kargo_file)

        for d in [df_tr, df_hb, df_maliyet, df_kargo]:
            d.columns = d.columns.str.strip()

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
                # Desi Kontrol: Trendyol'da yoksa maliyet listesinden al
                desi = to_float(row.get('Desi', 0))
                if desi <= 0: desi = to_float(m.iloc[0].get('Desi', 0))
                
                kargo = kargo_hesapla(desi, df_kargo)
                kom_tl = satis * (kom_oran / 100)
                net_kar = satis - (alis + kom_tl + kargo + sabit_gider_val)
                
                results.append({
                    "Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Maliyet": alis, 
                    "Komisyon": round(kom_tl, 2), "Kargo": kargo, "Platform Gideri": sabit_gider_val,
                    "Net Kar": round(net_kar, 2), "Kar Marjı %": round((net_kar/satis)*100, 2) if satis>0 else 0
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
                desi = to_float(m.iloc[0].get('Desi', 0)) # HB için maliyet desisi kullan
                
                kargo = kargo_hesapla(desi, df_kargo)
                kom_kdvli = (satis * (kom_oran / 100)) * 1.20
                tahsilat = satis * hb_tahsilat_oran
                net_kar = satis - (alis + kom_kdvli + tahsilat + kargo + sabit_gider_val)
                
                results.append({
                    "Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Satış": satis, "Maliyet": alis, 
                    "Komisyon(+KDV)": round(kom_kdvli, 2), "Kargo": kargo, "Tahsilat/Sabit": round(tahsilat + sabit_gider_val, 2),
                    "Net Kar": round(net_kar, 2), "Kar Marjı %": round((net_kar/satis)*100, 2) if satis>0 else 0
                })

        if results:
            st.success("Hesaplama Başarılı! (Tüm kesintiler dahil edildi)")
            st.dataframe(pd.DataFrame(results))
            output = io.BytesIO()
            pd.DataFrame(results).to_excel(output, index=False)
            st.download_button("Excel Raporu İndir", output.getvalue(), "Kar_Analiz.xlsx")
