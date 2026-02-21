# ... (Önceki matematiksel fonksiyonlar aynı kalıyor, altına şu analiz kısmını ekliyoruz) ...

        if results:
            final_df = pd.DataFrame(results)
            
            # --- STRATEJİK ÖZET PANELİ (YENİ) ---
            st.subheader("🤖 AI Strateji Danışmanı Notları")
            
            # 1. Analiz: En Karlı Marka
            en_karli_marka = final_df.groupby('Marka')['Marj %'].mean().idxmax()
            # 2. Analiz: En Çok Kar Ettiren Platform
            en_karli_plat = final_df.groupby('Platform')['Marj %'].mean().idxmax()
            # 3. Analiz: Acil Müdahale
            kritik_count = len(final_df[final_df['Marj %'] < 10])
            
            with st.expander("📌 Stratejik Önerileri Oku", expanded=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.info(f"**Marka Stratejisi:** Ortalama karlılıkta **{en_karli_marka}** önde gidiyor. Bu markanın ürünlerinde reklam bütçesini artırmak mantıklı olabilir.")
                    st.warning(f"**Kritik Uyarı:** Tam **{kritik_count}** üründe kar marjın %10'un altında! Bu ürünlerin kargo ve komisyon oranlarını acilen gözden geçir.")
                with col_b:
                    st.success(f"**Platform Verimliliği:** Şu an **{en_karli_plat}** platformu senin için daha karlı bir saha. Stok önceliğini buraya verebilirsin.")
                    st.write("🔍 *Öneri:* Kargo maliyeti satış fiyatının %15'ini geçen ürünleri 'Çoklu Paket' haline getirerek lojistik yükünü düşür.")

            # --- GÖRSEL GRAFİKLER ---
            # (Senin o güzel grafiklerin altına bu tabloları diziyoruz)
            
            # ... (Geri kalan grafik ve tablo kodları aynen devam eder) ...
