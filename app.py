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
        # Senin tablodaki DESİ kolonunu sayıya çevirelim
        kargo_df['DESİ'] = kargo_df['DESİ'].apply(to_float)
        
        if desi_val <= 30:
            # Desiden büyük veya eşit olan en küçük desi basamağını bul
            matched = kargo_df[kargo_df['DESİ'] >= desi_val].sort_values('DESİ')
            if not matched.empty:
                return float(matched.iloc[0]['Fiyat'])
            else:
                return 447.06 # 30 desi fiyatı
        else:
            # 30+ desi kuralı: 447.06 + (ek_desi * 14.87)
            return 447.06 + ((desi_val - 30) * 14.87)
    except:
        return 0.0

# --- YÜKLEME ALANI (SOL PANEL) ---
with st.sidebar:
    st.header("📂 Dosyaları Yükle")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi", type=['xlsx'])
    
    st.divider()
    st.subheader("⚙️ Gider Ayarları")
    tr_sabit = st.number_input("Trendyol Sabit Gider (TL)", value=15.0)
    hb_sabit = st.number_input("HB Sabit Gider (TL)", value=15.0)
    hb_tahsilat_oran = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100

# --- HESAPLAMA MOTORU ---
if st.button("HESAPLAMAYI BAŞLAT ✨"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen tüm dosyaları yükleyin!")
    else:
        df_tr = pd.read_excel(tr_file); df_tr.columns = df_tr.columns.str.strip()
        df_hb = pd.read_excel(hb_file); df_hb.columns = df_hb.columns.str.strip()
        df_maliyet = pd.read_excel(maliyet_file); df_maliyet.columns = df_maliyet.columns.str.strip()
        df_kargo = pd.read_excel(kargo_file); df_kargo.columns = df_kargo.columns.str.strip()

        results = []

        # --- TRENDYOL İŞLEME ---
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
                net_kar = satis - (alis + kom_tl + kargo + tr_sabit)
                
                results.append({
                    "Platform": "Trendyol", "Marka": row.get('Marka','-'), "Kod": row.get('Tedarikçi Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Desi": desi, "Satış": satis, "Maliyet": alis, 
                    "Komisyon %": kom_oran, "Komisyon TL": round(kom_tl, 2), "Tahsilat Bedeli": 0,
                    "Kargo": round(kargo, 2), "Platform Gideri": tr_sabit,
                    "Net Kar": round(net_kar, 2), "Kar Marjı %": round((net_kar/satis)*100, 2) if satis>0 else 0
                })

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
                
                kargo = kargo_hesapla(desi, df_kargo)
                kom_kdvli = (satis * (kom_oran / 100)) * 1.20 # HB Komisyon + %20 KDV
                tahsilat = satis * hb_tahsilat_oran
                net_kar = satis - (alis + kom_kdvli + tahsilat + kargo + hb_sabit)
                
                results.append({
                    "Platform": "Hepsiburada", "Marka": row.get('Marka','-'), "Kod": row.get('Satıcı Stok Kodu','-'),
                    "Ürün": row.get('Ürün Adı','-'), "Desi": desi, "Satış": satis, "Maliyet": alis, 
                    "Komisyon %": kom_oran, "Komisyon TL": round(kom_kdvli, 2), "Tahsilat Bedeli": round(tahsilat, 2),
                    "Kargo": round(kargo, 2), "Platform Gideri": hb_sabit,
                    "Net Kar": round(net_kar, 2), "Kar Marjı %": round((net_kar/satis)*100, 2) if satis>0 else 0
                })

        if results:
            final_df = pd.DataFrame(results)
            st.success("Analiz Tamamlandı! Tüm platform giderleri ve kargo detayları eklendi.")
            
            # Tabloyu göster
            st.dataframe(final_df, use_container_width=True)
            
            # Excel indirme
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Kar Analizi')
            st.download_button("📥 Tüm Analizi Excel Olarak İndir", output.getvalue(), "Pazaryeri_Analiz_Raporu.xlsx")
