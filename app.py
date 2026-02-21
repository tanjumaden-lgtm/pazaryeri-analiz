import streamlit as st
import pandas as pd
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pazaryeri Kar Analiz Paneli", layout="wide")
st.title("🚀 Pazaryeri Kar & Maliyet Analiz Sistemi")
st.markdown("Trendyol ve Hepsiburada verilerini maliyetlerinizle saniyeler içinde birleştirin.")

# --- YARDIMCI FONKSİYONLAR ---
def kargo_hesapla(desi, kargo_df):
    try:
        # Kargo tablosu başlık temizliği
        kargo_df.columns = kargo_df.columns.str.strip()
        if desi <= 30:
            # Tablodaki en yakın büyük veya eşit desiyi bulur
            return kargo_df.loc[kargo_df['DESİ'] >= desi, 'Fiyat'].iloc[0]
        else:
            # 30+ desi kuralı: 447.06 + ((ek_desi) * 14.87)
            return 447.06 + ((desi - 30) * 14.87)
    except:
        return 0

# --- DOSYA YÜKLEME ALANI (SOL PANEL) ---
with st.sidebar:
    st.header("📂 Dosyaları Yükle")
    tr_file = st.file_uploader("1. Trendyol Ürün Listesi", type=['xlsx'])
    hb_file = st.file_uploader("2. Hepsiburada Ürün Listesi", type=['xlsx'])
    maliyet_file = st.file_uploader("3. Maliyet Listesi (Barkod, StokKodu, Ürün Adı, Alış Fiyatı, Desi)", type=['xlsx'])
    kargo_file = st.file_uploader("4. Kargo Fiyat Listesi (DESİ, Fiyat)", type=['xlsx'])
    
    st.divider()
    st.subheader("⚙️ Gizli Gider Ayarları")
    sabit_gider = st.number_input("Platform Sabit Gider (TL)", value=15.0)
    hb_tahsilat = st.number_input("HB Tahsilat Bedeli (%)", value=0.8) / 100

# --- ANA HESAPLAMA MOTORU ---
if st.button("ANALİZİ BAŞLAT ✨"):
    if not (tr_file and hb_file and maliyet_file and kargo_file):
        st.error("Lütfen dört Excel dosyasını da yüklediğinizden emin olun!")
    else:
        # Excel'leri Oku ve Başlıkları Temizle
        df_tr = pd.read_excel(tr_file)
        df_tr.columns = df_tr.columns.str.strip()
        
        df_hb = pd.read_excel(hb_file)
        df_hb.columns = df_hb.columns.str.strip()
        
        df_maliyet = pd.read_excel(maliyet_file)
        df_maliyet.columns = df_maliyet.columns.str.strip()
        
        df_kargo = pd.read_excel(kargo_file)
        df_kargo.columns = df_kargo.columns.str.strip()
        
        results = []
        errors = []

        # --- ÜÇLÜ EŞLEŞTİRME FONKSİYONU ---
        def maliyet_bul(p_barkod, p_stok, p_ad):
            # 1. Barkod ile ara
            m = df_maliyet[df_maliyet['Barkod'].astype(str) == str(p_barkod)]
            if m.empty:
                # 2. StokKodu ile ara
                m = df_maliyet[df_maliyet['StokKodu'].astype(str) == str(p_stok)]
            if m.empty:
                # 3. Ürün Adı ile ara
                m = df_maliyet[df_maliyet['Ürün Adı'].astype(str) == str(p_ad)]
            return m

        # --- TRENDYOL İŞLEME ---
        for _, row in df_tr.iterrows():
            match = maliyet_bul(row.get('Barkod'), row.get('Tedarikçi Stok Kodu'), row.get('Ürün Adı'))
            
            if not match.empty:
                alis = match.iloc[0]['Alış Fiyatı']
                desi = row.get('Desi', match.iloc[0].get('Desi', 0))
                kargo_tl = kargo_hesapla(desi, df_kargo)
                satis = row.get("Trendyol'da Satılacak Fiyat (KDV Dahil)", 0)
                kom_tl = satis * (row.get('Komisyon Oranı', 0) / 100)
                
                net_kar = satis - (alis + kom_tl + kargo_tl + sabit_gider)
                results.append({
                    "Platform": "Trendyol", "Marka": row.get('Marka', '-'), "Kod": row.get('Tedarikçi Stok Kodu', '-'),
                    "Ürün": row.get('Ürün Adı', '-'), "Satış": satis, "Maliyet": alis, "Kargo": kargo_tl, "Komisyon": kom_tl, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Trendyol", "Kod": row.get('Tedarikçi Stok Kodu', '-'), "İsim": row.get('Ürün Adı', '-'), "Hata": "Eşleşme Bulunamadı"})

        # --- HEPSİBURADA İŞLEME ---
        for _, row in df_hb.iterrows():
            match = maliyet_bul(row.get('Barkod'), row.get('Satıcı Stok Kodu'), row.get('Ürün Adı'))
            
            if not match.empty:
                alis = match.iloc[0]['Alış Fiyatı']
                # HB'de desi bilgisi genelde yoktur, maliyet tablosundan çekiyoruz
                desi_val = match.iloc[0].get('Desi', 0)
                kargo_tl = kargo_hesapla(desi_val, df_kargo)
                satis = row.get('Fiyat', 0)
                # HB Özel: (Komisyon + KDV) + Tahsilat Bedeli + Sabit Gider
                kom_kdvli = (satis * (row.get('Komisyon Oranı', 0) / 100)) * 1.20
                tahsilat_tl = satis * hb_tahsilat
                
                net_kar = satis - (alis + kom_kdvli + tahsilat_tl + kargo_tl + sabit_gider)
                results.append({
                    "Platform": "Hepsiburada", "Marka": row.get('Marka', '-'), "Kod": row.get('Satıcı Stok Kodu', '-'),
                    "Ürün": row.get('Ürün Adı', '-'), "Satış": satis, "Maliyet": alis, "Kargo": kargo_tl, "Komisyon": kom_kdvli, "Net Kar": net_kar
                })
            else:
                errors.append({"Platform": "Hepsiburada", "Kod": row.get('Satıcı Stok Kodu', '-'), "İsim": row.get('Ürün Adı', '-'), "Hata": "Eşleşme Bulunamadı"})

        # --- SONUÇLARI GÖSTER ---
        if results:
            final_df = pd.DataFrame(results)
            final_df["Kar Marjı %"] = (final_df["Net Kar"] / final_df["Satış"]) * 100

            st.success("Hesaplama Başarıyla Tamamlandı!")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Satış Adedi", len(final_df))
            m2.metric("Ortalama Marj", f"%{final_df['Kar Marjı %'].mean():.2f}")
            m3.metric("Toplam Net Kar", f"{final_df['Net Kar'].sum():,.2f} TL")

            st.dataframe(final_df.style.highlight_min(axis=0, subset=['Net Kar'], color='#FFC0CB'))

            # Excel Çıktısı
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Analiz Raporu')
            st.download_button("📥 Analiz Sonuçlarını İndir", data=output.getvalue(), file_name="Pazaryeri_Kar_Analiz.xlsx")
        else:
            st.warning("Eşleşen ürün bulunamadı. Lütfen Excel dosyalarındaki barkod ve ürün isimlerini kontrol edin.")

        if errors:
            with st.expander("⚠️ Eşleşmeyen Ürünler Listesi"):
                st.table(pd.DataFrame(errors))
