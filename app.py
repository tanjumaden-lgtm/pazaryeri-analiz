import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")
st.title("🚀 Pazaryeri Kar & Maliyet Analiz Sistemi")
st.markdown("Trendyol ve Hepsiburada verilerini maliyetlerinizle saniyeler içinde birleştirin.")

# --- YARDIMCI FONKSİYONLAR ---
def kargo_hesapla(desi, kargo_df):
    """30 desi ve üzeri için özel fiyatlandırma kuralı"""
    try:
        if desi <= 30:
            # Tablodaki en yakın büyük veya eşit desiyi bulur
            return kargo_df.loc[kargo_df['DESİ'] >= desi, 'Fiyat'].iloc[0]
        else:
            # 30+ kuralı: 447.06 + (ek desi * 14.87)
            return 447.06 + ((desi - 30) * 14.87)
    except:
        return 0

# --- DOSYA YÜKLEME ALANI (SOL PANEL) ---
with st.sidebar:
    st.header("📂 Dosyaları Yükle")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi (Barkod, Stok Kodu, Alis_Fiyati, Desi)", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi (DESİ, Fiyat)", type=['xlsx'])
    
    st.divider()
    st.subheader("⚙️ Gizli Gider Ayarları")
    sabit_gider = st.number_input("Platform Sabit Gider (TL)", value=15.0)
    hb_tahsilat = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100

# --- ANA HESAPLAMA MOTORU ---
if st.button("HESAPLAMAYI BAŞLAT ✨"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen tüm Excel dosyalarını yüklediğinizden emin olun!")
    else:
        # Dosyaları Oku
        df_tr = pd.read_excel(tr_file)
        df_hb = pd.read_excel(hb_file)
        df_maliyet = pd.read_excel(maliyet_file)
        df_kargo = pd.read_excel(kargo_file)
        
        results = []
        errors = []

        # --- TRENDYOL İŞLEME ---
        for _, row in df_tr.iterrows():
            # Barkod veya Stok Kodu ile eşleşme ara
            match = df_maliyet[(df_maliyet['Barkod'] == row['Barkod']) | 
                               (df_maliyet['Stok Kodu'] == row['Tedarikçi Stok Kodu'])]
            
            if not match.empty:
                maliyet = match.iloc[0]['Alis_Fiyati']
                desi = row['Desi']
                kargo_tl = kargo_hesapla(desi, df_kargo)
                satis = row["Trendyol'da Satılacak Fiyat (KDV Dahil)"]
                kom_tl = satis * (row['Komisyon Oranı'] / 100)
                
                net_kar = satis - (maliyet + kom_tl + kargo_tl + sabit_gider)
                results.append({
                    "Platform": "Trendyol", "Marka": row['Marka'], "Kod": row['Tedarikçi Stok Kodu'],
                    "Satış": satis, "Maliyet": maliyet, "Kargo": kargo_tl, "Komisyon": kom_tl, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Trendyol", "Kod": row['Tedarikçi Stok Kodu'], "Hata": "Maliyet Bulunamadı"})

        # --- HEPSİBURADA İŞLEME ---
        for _, row in df_hb.iterrows():
            match = df_maliyet[(df_maliyet['Barkod'] == row['Barkod']) | 
                               (df_maliyet['Stok Kodu'] == row['Satıcı Stok Kodu'])]
            
            if not match.empty:
                maliyet = match.iloc[0]['Alis_Fiyati']
                # HB'de desi bilgisi yoksa maliyet listesindeki desiyi kullan
                desi_val = match.iloc[0]['Desi'] if 'Desi' in match.columns else 0
                kargo_tl = kargo_hesapla(desi_val, df_kargo)
                satis = row['Fiyat']
                # HB Özel: Komisyon + KDV (%20) + Tahsilat Bedeli
                kom_kdvli = (satis * (row['Komisyon Oranı'] / 100)) * 1.20
                tahsilat_tl = satis * hb_tahsilat
                
                net_kar = satis - (maliyet + kom_kdvli + tahsilat_tl + kargo_tl + sabit_gider)
                results.append({
                    "Platform": "Hepsiburada", "Marka": row['Marka'], "Kod": row['Satıcı Stok Kodu'],
                    "Satış": satis, "Maliyet": maliyet, "Kargo": kargo_tl, "Komisyon": kom_kdvli, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Hepsiburada", "Kod": row['Satıcı Stok Kodu'], "Hata": "Maliyet Bulunamadı"})

        # --- SONUÇLARI GÖSTER ---
        if results:
            final_df = pd.DataFrame(results)
            final_df["Kar Marjı %"] = (final_df["Net Kar"] / final_df["Satış"]) * 100

            st.success("Analiz Başarıyla Tamamlandı!")
            
            # Üst Panel Özet Rakamlar
            c1, c2, c3 = st.columns(3)
            c1.metric("Analiz Edilen Ürün", len(final_df))
            c2.metric("Ortalama Kar Marjı", f"%{final_df['Kar Marjı %'].mean():.2f}")
            c3.metric("Toplam Tahmini Net Kar", f"{final_df['Net Kar'].sum():,.2f} TL")

            # Ana Tablo
            st.dataframe(final_df.style.highlight_max(axis=0, subset=['Net Kar'], color='#90EE90'))

            # Excel İndirme Alanı
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Kar Analizi')
            st.download_button(
                label="📥 Analiz Sonuçlarını Excel Olarak İndir",
                data=output.getvalue(),
                file_name="Pazaryeri_Kar_Analiz_Raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Eşleşen ürün bulunamadı. Lütfen barkodları kontrol edin.")

        # Hatalı/Eşleşmeyen Ürünler Paneli
        if errors:
            with st.expander("⚠️ Maliyeti Bulunamayan (Eşleşmeyen) Ürünler"):
                st.write("Aşağıdaki ürünler maliyet listenizde bulunamadığı için hesaplanamadı:")
                st.table(pd.DataFrame(errors))
