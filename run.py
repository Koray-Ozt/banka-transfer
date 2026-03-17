import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import io
import re
import csv

# ==========================================
# 1. ARAYÜZ AYARLARI VE CSS (Masaüstü Tam Ekran)
# ==========================================
st.set_page_config(page_title="Akıllı Virman Yönetimi", layout="wide", page_icon="🏦", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main-header { font-size: 28px; font-weight: 700; color: #0f172a; margin-bottom: 0px; text-align: center; }
    .sub-header { font-size: 15px; color: #64748b; margin-bottom: 25px; text-align: center; font-weight: 400;}
    
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    
    .custom-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: transparent; color: #94a3b8; text-align: center;
        padding: 12px; font-size: 13px; font-weight: 500; z-index: 100; pointer-events: none;
    }
    .stAlert { border-radius: 10px !important; }
    </style>
    <div class="custom-footer">made with ❤️ by Koray Öztürk</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Mükerrer Kayıt ve Virman Yönetimi</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Dinamik Havuz Mimarisi ve Çoklu Seçenekli Eşleştirme Motoru</div>', unsafe_allow_html=True)

# ==========================================
# 2. DURUM (SESSION STATE) BAŞLATICILARI
# ==========================================
if 'analiz_yapildi' not in st.session_state: st.session_state.analiz_yapildi = False
if 'ham_veriler' not in st.session_state: st.session_state.ham_veriler = None
if 'raw_files' not in st.session_state: st.session_state.raw_files = {} 
if 'tum_eslesmeler' not in st.session_state: st.session_state.tum_eslesmeler = []

# YENİ: Dinamik Havuz Hafızası
if 'islenen_gidenler' not in st.session_state: st.session_state.islenen_gidenler = set()
if 'islenen_gelenler' not in st.session_state: st.session_state.islenen_gelenler = set()
if 'reddedilen_ciftler' not in st.session_state: st.session_state.reddedilen_ciftler = set()
if 'onaylanan_silinecekler' not in st.session_state: st.session_state.onaylanan_silinecekler = []
if 'islem_gecmisi' not in st.session_state: st.session_state.islem_gecmisi = []

if 'firma_girdisi' not in st.session_state: st.session_state.firma_girdisi = ""
if 'dinamik_firma_kelimeleri' not in st.session_state: st.session_state.dinamik_firma_kelimeleri = []
if 'maks_gun_farki' not in st.session_state: st.session_state.maks_gun_farki = 4

# ==========================================
# JAVASCRIPT: KLAVYE KISAYOLLARI (1, 2, 3, W, A, D)
# ==========================================
components.html("""
<script>
const doc = window.parent.document;
if (!doc.getElementById('keyboard_shortcuts_injected')) {
    const marker = doc.createElement('div');
    marker.id = 'keyboard_shortcuts_injected';
    marker.style.display = 'none';
    doc.body.appendChild(marker);

    doc.addEventListener('keydown', function(e) {
        const activeTag = doc.activeElement ? doc.activeElement.tagName.toLowerCase() : '';
        const isInput = ['input', 'textarea', 'select'].includes(activeTag) || doc.activeElement.isContentEditable;
        if (isInput) return; 
        
        const key = e.key;
        let btnTextToFind = null;

        if (key === 'ArrowRight' || key.toLowerCase() === 'd') btnTextToFind = 'Onayla (D';
        else if (key === 'ArrowLeft' || key.toLowerCase() === 'a') btnTextToFind = 'Yanlış Eşleşme (A';
        else if (key === 'ArrowUp' || key.toLowerCase() === 'w') btnTextToFind = 'Geri Dön (W';
        else if (key === '1') btnTextToFind = 'Çıkış Virman Değil (1';
        else if (key === '2') btnTextToFind = 'Giriş Virman Değil (2';
        else if (key === '3') btnTextToFind = 'İkisi de Virman Değil (3';

        if (btnTextToFind) {
            const buttons = Array.from(doc.querySelectorAll('button'));
            const btn = buttons.find(b => b.innerText.includes(btnTextToFind));
            if (btn && !btn.disabled) { e.preventDefault(); btn.click(); }
        }
    }, {passive: false});
}
</script>
""", height=0)

# ==========================================
# 3. MERKEZİ AYARLAR MENÜSÜ
# ==========================================
with st.expander("⚙️ PARAMETRE AYARLARI (Aç / Kapat)", expanded=False):
    st.markdown("Virman tespitini güçlendirmek için işlem yapılan firmanın adını girin ve valör toleransını belirleyin.")
    with st.form("ayarlar_formu"):
        col_a, col_b = st.columns(2)
        with col_a:
            yeni_firma_girdisi = st.text_input("Firma Unvanı / Kısa Adı", value=st.session_state.firma_girdisi, placeholder="Örn: ABC A.Ş., XYZ Ticaret")
        with col_b:
            yeni_maks_gun = st.slider("Valör Toleransı (Gün)", min_value=0, max_value=15, value=st.session_state.maks_gun_farki)
        ayarlari_kaydet = st.form_submit_button("💾 Ayarları Kaydet", use_container_width=True)
        
    if ayarlari_kaydet:
        st.session_state.firma_girdisi = yeni_firma_girdisi
        st.session_state.dinamik_firma_kelimeleri = [k.strip().upper() for k in yeni_firma_girdisi.split(',') if len(k.strip()) > 2]
        st.session_state.maks_gun_farki = yeni_maks_gun
        st.success("Ayarlar başarıyla kaydedildi! Analize başlayabilirsiniz.")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 4. SIFIR VERİ KAYBI VE OKUMA MOTORU
# ==========================================
def banka_dosyasi_oku(dosya):
    veri_bytes = dosya.read()
    dosya.seek(0)
    try:
        df = pd.read_excel(io.BytesIO(veri_bytes), header=None)
        if len(df.columns) >= 3: return df.fillna('') 
    except: pass
    try:
        dfs = pd.read_html(io.BytesIO(veri_bytes))
        if dfs and len(dfs) > 0:
            dfs.sort(key=lambda x: len(x), reverse=True) 
            return dfs[0].fillna('')
    except: pass
    metin = ""
    for enc in ['ISO-8859-9', 'cp1254', 'utf-8']:
        try: metin = veri_bytes.decode(enc); break
        except: continue
    if not metin: metin = veri_bytes.decode('utf-8', errors='ignore')
    satirlar = metin.splitlines()
    noktali_virgul = sum(s.count(';') for s in satirlar[:50])
    virgul = sum(s.count(',') for s in satirlar[:50])
    tab_sayisi = sum(s.count('\t') for s in satirlar[:50])
    ayrac = '\t' if (tab_sayisi > noktali_virgul and tab_sayisi > virgul) else (';' if noktali_virgul > virgul else ',')
    reader = csv.reader(io.StringIO(metin), delimiter=ayrac)
    try: return pd.DataFrame(list(reader)).fillna('')
    except: return None

def tutar_temizle(deger):
    if pd.isna(deger) or str(deger).strip() == '': return 0.0
    deger_str = str(deger).upper().replace('TL', '').replace(' ', '').strip()
    if not deger_str or deger_str == 'NAN': return 0.0
    carpan = -1 if deger_str.startswith('-') or deger_str.endswith('-') else 1
    deger_str = deger_str.replace('-', '')
    if ',' in deger_str and '.' in deger_str:
        if deger_str.rfind(',') > deger_str.rfind('.'): deger_str = deger_str.replace('.', '').replace(',', '.')
        else: deger_str = deger_str.replace(',', '')
    elif ',' in deger_str: deger_str = deger_str.replace(',', '.')
    try: return float(deger_str) * carpan
    except: return 0.0

def baslik_satirini_bul(df):
    for i in range(min(50, len(df))):
        satir_str = " ".join([str(x).upper() for x in df.iloc[i].values])
        if any(k in satir_str for k in ['TARİH', 'TARIH', 'TAR]H', ']~LEM', 'DATE', 'ZAMAN', 'MUHTAR']) and any(k in satir_str for k in ['TUTAR', 'BORC', 'BORÇ', 'BORG', 'ALACAK', 'MEBLA']): return i
    return 0

def veriyi_standartlastir(df_raw, dosya_adi):
    baslik_idx = baslik_satirini_bul(df_raw)
    df = df_raw.iloc[baslik_idx+1:].copy()
    orijinal_indexler = df.index.values 
    df = df.reset_index(drop=True)
    orijinal_kolonlar = df_raw.iloc[baslik_idx].astype(str).str.upper().str.replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', regex=True).str.strip().tolist()
    df.columns = [f"{col}_{i}" if orijinal_kolonlar.count(col) > 1 or not col else col for i, col in enumerate(orijinal_kolonlar)]
    df = df.astype(str).replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', regex=True)
    st_df = pd.DataFrame()
    st_df['KAYNAK'] = [dosya_adi] * len(df)
    st_df['ORIJINAL_INDEX'] = orijinal_indexler 
    
    tarih_kolonu = next((c for c in df.columns if any(k in c for k in ['TARİH', 'TARIH', 'TAR]H', 'TARIHI', 'HAREKETISLEMTARIHI', 'MUH TARİH'])), None)
    if tarih_kolonu:
        df['GECICI_TARIH'] = df[tarih_kolonu].astype(str).str.extract(r'(\d{2,4}[./-]\d{2}[./-]\d{2,4})')[0]
        df['GECICI_TARIH'] = df['GECICI_TARIH'].fillna(df[tarih_kolonu].astype(str))
        st_df['TARİH'] = pd.to_datetime(df['GECICI_TARIH'], errors='coerce', dayfirst=True).dt.strftime('%d.%m.%Y')
    else: return pd.DataFrame()

    saat_kolonu = next((c for c in df.columns if any(k in c for k in ['SAAT', 'ZAMAN'])), None)
    if saat_kolonu:
        saat_df = df[saat_kolonu].astype(str).str.extract(r'([01]?[0-9]|2[0-3])[:.]([0-5][0-9])')
        st_df['SAAT'] = np.where(saat_df[0].notna(), saat_df[0] + ':' + saat_df[1], '00:00')
    else:
        saat_df = df[tarih_kolonu].astype(str).str.extract(r'(?:\s|-|T)([01]?[0-9]|2[0-3])[:.]([0-5][0-9])')
        st_df['SAAT'] = np.where(saat_df[0].notna(), saat_df[0] + ':' + saat_df[1], '00:00')

    st_df['TARIH_SAAT_OBJ'] = pd.to_datetime(st_df['TARİH'] + ' ' + st_df['SAAT'], format='%d.%m.%Y %H:%M', errors='coerce')

    aciklama_kolonu = None
    for k in ['AÇIKLAMA', 'ACIKLAMA', 'AGIKLAMA', 'AG}KLAMA', 'AÇIKLAMAS', 'FISACIKLAMA', 'DETAY', 'REFERANS']:
        bulunan = [c for c in df.columns if k in c]
        if bulunan: aciklama_kolonu = bulunan[0]; break
    st_df['AÇIKLAMA'] = df[aciklama_kolonu] if aciklama_kolonu else ""

    tutar_kolonu = next((c for c in df.columns if any(k in c for k in ['TUTAR', 'MEBLA', 'HAREKETTUTAR'])), None)
    ba_kolonu = next((c for c in df.columns if any(k in c for k in ['B/A', 'BORCALACAK', 'BORÇ/ALACAK', 'BORG/ALACAK'])), None)
    borc_kolonu = next((c for c in df.columns if any(k in c for k in ['BORÇ', 'BORC', 'BORG']) and 'ALACAK' not in c and '/' not in c), None)
    alacak_kolonu = next((c for c in df.columns if 'ALACAK' in c and 'BORC' not in c and '/' not in c), None)

    if borc_kolonu and alacak_kolonu: st_df['TUTAR'] = df[alacak_kolonu].apply(tutar_temizle) - df[borc_kolonu].apply(tutar_temizle)
    elif tutar_kolonu and ba_kolonu:
        is_borc = df[ba_kolonu].astype(str).str.upper().str.startswith('B')
        st_df['TUTAR'] = np.where(is_borc, -df[tutar_kolonu].apply(tutar_temizle).abs(), df[tutar_kolonu].apply(tutar_temizle).abs())
    elif tutar_kolonu: st_df['TUTAR'] = df[tutar_kolonu].apply(tutar_temizle)
    else: return pd.DataFrame()

    st_df = st_df.dropna(subset=['TARİH']).reset_index(drop=True)
    st_df = st_df[st_df['TUTAR'] != 0].reset_index(drop=True)
    
    st_df['VIRMAN_ADAYI'] = True
    haric_kelimeler = [
        'GİDER PUSULAS', 'GIDER PUSULAS', 'BSMV', 'MASRAF', 'KOMİSYON', 'KOMISYON', 'KOM.', 
        'ÜCRET', 'UCRET', 'KDV', 'VERGİ', 'VERGI', 'STOPAJ', 'FAİZ', 'FAIZ', 'PŞNSTŞ', 'PSNSTS', 
        'POS ', 'TAKAS', 'İŞLETİM', 'ISLETIM', 'HİZMET', 'HIZMET', 'KESİNTİ', 'KESINTI', 'KART TAHSİLAT', 'VERGİSİ'
    ]
    st_df.loc[st_df['AÇIKLAMA'].astype(str).str.upper().str.contains('|'.join(haric_kelimeler), regex=True, na=False), 'VIRMAN_ADAYI'] = False
    ticari_regex = r'(ALT[Iİ]N|ALTI|ALTN).{0,5}(AL[Iİ]M|BEDEL[Iİ])|AL[Iİ]M.{0,5}BEDEL[Iİ]|ELDEN.{0,5}TESL[Iİ]M|TESL[Iİ]M.{0,5}ALD[Iİ]M'
    st_df.loc[st_df['AÇIKLAMA'].astype(str).str.upper().str.contains(ticari_regex, regex=True, na=False), 'VIRMAN_ADAYI'] = False
    return st_df.reset_index(drop=True)

# ==========================================
# 5. BANKA DEDEKTİFİ & TÜM OLASILIKLARI BULMA
# ==========================================
def banka_bul(metin):
    metin = str(metin).upper()
    bulunanlar = set()
    kisa_kodlar = {'TEB': r'\bTEB\b', 'QNB': r'\bQNB\b', 'YAPI KREDİ': r'\bYKB\b', 'ING': r'\bİ?NG\b', 'HALKBANK': r'\bHALK\b', 'VAKIFBANK': r'\bVAKIF\b'}
    for banka, desen in kisa_kodlar.items():
        if re.search(desen, metin): bulunanlar.add(banka)
    uzun_isimler = {
        'TEB': ['EKONOMİ BANK', 'EKONOMI BANK', 'TÜRK EKONOMİ', 'TURK EKONOMI'], 'GARANTİ': ['GARANTİ', 'GARANTI'],
        'ZİRAAT': ['ZİRAAT', 'ZIRAAT', 'ZIRAATBANK'], 'HALKBANK': ['HALKBANK', 'HALK BANK', 'T.HALK'],
        'VAKIFBANK': ['VAKIFBANK', 'VAKIF BANK', 'VAKIF KATILIM'], 'AKBANK': ['AKBANK', 'AK BANK'],
        'YAPI KREDİ': ['YAPI KREDİ', 'YAPI KREDI', 'YAPI VE KREDİ', 'KOCBANK', 'KOÇBANK'],
        'İŞ BANKASI': ['İŞ BANK', 'IS BANK', 'İŞBANK', 'ISBANK', 'İŞ CEP', 'İS CEP', 'İŞBANKASI', 'ISBANKASI'],
        'QNB': ['FİNANSBANK', 'FINANSBANK', 'ENPARA', 'FİNANS BANK', 'FINANS BANK'], 'DENİZBANK': ['DENİZBANK', 'DENIZBANK', 'DENİZ BANK', 'DENIZ BANK'],
        'KUVEYT TÜRK': ['KUVEYT', 'KUVEYTTURK'], 'ALBARAKA': ['ALBARAKA', 'AL BARAKA'], 'ODEA': ['ODEABANK', 'ODEA BANK'],
        'FİBABANKA': ['FİBABANKA', 'FIBABANKA'], 'ŞEKERBANK': ['ŞEKERBANK', 'SEKERBANK'], 'PAPARA': ['PAPARA']
    }
    for banka_adi, kelimeler in uzun_isimler.items():
        if any(k in metin for k in kelimeler): bulunanlar.add(banka_adi)
    return list(bulunanlar)

KELIME_DESENI = re.compile(r'[A-ZĞÜŞİÖÇ0-9]{3,}')

def virman_puanla_ve_bul(df, sirket_kelimeleri, maks_gun):
    df = df.reset_index(drop=True)
    adaylar_df = df[df['VIRMAN_ADAYI'] == True].copy()
    adaylar_df['MUTLAK_TUTAR'] = adaylar_df['TUTAR'].abs()
    grup = adaylar_df.groupby('MUTLAK_TUTAR')
    
    tum_eslesmeler = []
    dosya_bankalari = {dosya_adi: (banka_bul(dosya_adi)[0] if banka_bul(dosya_adi) else None) for dosya_adi in df['KAYNAK'].unique()}
    kesin_virman_kelimeleri = ['VİRMAN', 'VIRMAN', 'KENDİ', 'KENDI', 'TRANSFER', 'MAHSUP'] + sirket_kelimeleri
    jenerikler = {'İLE', 'İÇİN', 'BANK', 'BANKASI', 'ŞUBESİ', 'HAVALE', 'GÖNDEREN', 'ALICI', 'İŞLEMLERİ', 'BEDELİ', 'ELDEN', 'TESLİM', 'ALDIM', 'NOLU', 'GİDEN', 'GELEN', 'ÖDEME', 'ÖDEMESİ', 'HESABA', 'HESAPTAN', 'FAST', 'EFT', 'SWIFT', 'İBAN', 'IBAN', 'SANAYİ', 'TİCARET', 'KUYUMCULUK', 'ALTIN', 'ALIMI', 'ALIM', 'SATIM', 'SATIŞ', 'A.Ş.', 'A.S.', 'LTD.', 'ŞTİ.', 'LİMİTED', 'ŞİRKETİ', 'SORG', 'NO', 'TÜRK', 'A.S', 'A.Ş'}
    
    for tutar, data in grup:
        if len(data) > 1:
            artilar = data[data['TUTAR'] > 0] 
            eksiler = data[data['TUTAR'] < 0] 
            if not artilar.empty and not eksiler.empty:
                for i, arti in artilar.iterrows():
                    kelimeler_gelen = set([w for w in KELIME_DESENI.findall(str(arti['AÇIKLAMA']).upper()) if w not in jenerikler])
                    tarih_arti = pd.to_datetime(arti['TARİH'], format='%d.%m.%Y')
                    gelen_gercek_banka = dosya_bankalari.get(arti['KAYNAK'])
                    gelen_aciklama_bankalari = banka_bul(arti['AÇIKLAMA'])
                    
                    for j, eksi in eksiler.iterrows():
                        tarih_eksi = pd.to_datetime(eksi['TARİH'], format='%d.%m.%Y')
                        gun_farki_gercek = (tarih_arti - tarih_eksi).days
                        if gun_farki_gercek < 0 or gun_farki_gercek > maks_gun: continue 
                            
                        dakika_farki_gercek = 0
                        if (arti['SAAT'] != '00:00' and eksi['SAAT'] != '00:00' and pd.notna(arti['TARIH_SAAT_OBJ']) and pd.notna(eksi['TARIH_SAAT_OBJ'])):
                            dakika_farki_gercek = (arti['TARIH_SAAT_OBJ'] - eksi['TARIH_SAAT_OBJ']).total_seconds() / 60
                            if dakika_farki_gercek < 0: continue # ZAMAN PARADOKSU: Giden saat, Gelen saatten büyük olamaz.
                                
                        giden_gercek_banka = dosya_bankalari.get(eksi['KAYNAK'])
                        giden_aciklama_bankalari = banka_bul(eksi['AÇIKLAMA'])
                        puan, nedenler = 0, []
                        
                        if gun_farki_gercek == 0: 
                            puan += 35
                            if (arti['SAAT'] != '00:00' and eksi['SAAT'] != '00:00' and pd.notna(arti['TARIH_SAAT_OBJ']) and pd.notna(eksi['TARIH_SAAT_OBJ'])):
                                if 0 <= dakika_farki_gercek <= 15:
                                    puan += 30; nedenler.append(f"Saat Eşleşmesi (<15 Dk)")
                                elif 15 < dakika_farki_gercek <= 60:
                                    puan += 15; nedenler.append(f"Yakın Saat ({int(dakika_farki_gercek)} Dk)")
                                else: nedenler.append("Aynı Gün")
                            else: nedenler.append("Aynı Gün")
                        elif gun_farki_gercek <= 2: puan += 20; nedenler.append(f"{gun_farki_gercek} Gün Farkı")
                        else: puan += 10; nedenler.append(f"Esnek Valör")
                        
                        if arti['KAYNAK'] != eksi['KAYNAK']: puan += 10; nedenler.append("Farklı Bankalar")
                        
                        farkli_banka_suphesi = False
                        if giden_aciklama_bankalari and giden_gercek_banka and gelen_gercek_banka:
                            for b in giden_aciklama_bankalari:
                                if b != giden_gercek_banka and b != gelen_gercek_banka: farkli_banka_suphesi = True; break
                        if not farkli_banka_suphesi and gelen_aciklama_bankalari and giden_gercek_banka and gelen_gercek_banka:
                            for b in gelen_aciklama_bankalari:
                                if b != giden_gercek_banka and b != gelen_gercek_banka: farkli_banka_suphesi = True; break
                        
                        if farkli_banka_suphesi: puan -= 30; nedenler.append("Farklı Banka Şüphesi")
                        if gelen_gercek_banka and gelen_gercek_banka in giden_aciklama_bankalari: puan += 30; nedenler.append(f"Banka Teyidi")
                        if giden_gercek_banka and giden_gercek_banka in gelen_aciklama_bankalari: puan += 30; nedenler.append(f"Banka Teyidi")

                        aciklama_birlesik = (str(arti['AÇIKLAMA']) + " " + str(eksi['AÇIKLAMA'])).upper()
                        if any(k in aciklama_birlesik for k in kesin_virman_kelimeleri): puan += 40; nedenler.append("Firma İbaresi")
                            
                        kelimeler_giden = set([w for w in KELIME_DESENI.findall(str(eksi['AÇIKLAMA']).upper()) if w not in jenerikler])
                        ortak_kelimeler = kelimeler_giden.intersection(kelimeler_gelen)
                        if ortak_kelimeler: puan += 30; nedenler.append(f"Ortak Terim")
                            
                        if puan >= 55:
                            tum_eslesmeler.append({
                                'Olasılık': min(puan, 100), 'Tutar': tutar, 
                                'Giden_Banka': eksi['KAYNAK'].split('.')[0], 'Gelen_Banka': arti['KAYNAK'].split('.')[0],
                                'Giden_Aciklama': eksi['AÇIKLAMA'], 'Gelen_Aciklama': arti['AÇIKLAMA'],
                                'Giden_Tarih': f"{eksi['TARİH']} {eksi['SAAT'] if eksi['SAAT'] != '00:00' else ''}",
                                'Gelen_Tarih': f"{arti['TARİH']} {arti['SAAT'] if arti['SAAT'] != '00:00' else ''}",
                                'Giden_Tutar': eksi['TUTAR'], 'Gelen_Tutar': arti['TUTAR'],
                                'Nedeni': " + ".join(nedenler), 'silinecek_index': i, 'giden_index': j
                            })
                            
    # Bütün olası eşleşmeleri puana göre dizip listeyi döndürüyoruz (Filtreleme işlemi UI tarafında dinamik yapılacak)
    tum_eslesmeler.sort(key=lambda x: x['Olasılık'], reverse=True)
    return tum_eslesmeler

# ==========================================
# 6. DİNAMİK HAVUZ YÖNETİMİ (AKILLI AKSİYONLAR)
# ==========================================
def gecmisi_kaydet():
    st.session_state.islem_gecmisi.append({
        'gidenler': set(st.session_state.islenen_gidenler),
        'gelenler': set(st.session_state.islenen_gelenler),
        'reddedilen': set(st.session_state.reddedilen_ciftler),
        'silinenler': list(st.session_state.onaylanan_silinecekler)
    })

def aksiyon_al(aksiyon_tipi, giden_idx, gelen_idx):
    gecmisi_kaydet()
    if aksiyon_tipi == 'ONAYLA':
        st.session_state.islenen_gidenler.add(giden_idx)
        st.session_state.islenen_gelenler.add(gelen_idx)
        st.session_state.onaylanan_silinecekler.append(gelen_idx)
    elif aksiyon_tipi == 'YANLIS_ESLESME':
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx)) # İkisi de havuza döner
    elif aksiyon_tipi == 'GIDEN_DEGIL':
        st.session_state.islenen_gidenler.add(giden_idx) # Giden çöpe, Gelen havuza
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx))
    elif aksiyon_tipi == 'GELEN_DEGIL':
        st.session_state.islenen_gelenler.add(gelen_idx) # Gelen çöpe, Giden havuza
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx))
    elif aksiyon_tipi == 'IKISI_DE_DEGIL':
        st.session_state.islenen_gidenler.add(giden_idx) # İkisi de çöpe
        st.session_state.islenen_gelenler.add(gelen_idx)

def geri_al():
    if st.session_state.islem_gecmisi:
        son_durum = st.session_state.islem_gecmisi.pop()
        st.session_state.islenen_gidenler = set(son_durum['gidenler'])
        st.session_state.islenen_gelenler = set(son_durum['gelenler'])
        st.session_state.reddedilen_ciftler = set(son_durum['reddedilen'])
        st.session_state.onaylanan_silinecekler = list(son_durum['silinenler'])

# ==========================================
# 7. ANA EKRAN VE SONUÇLAR
# ==========================================
yuklenen_dosyalar = st.file_uploader("İşlenecek Ekstreleri Yükleyin", type=["csv", "xls", "xlsx"], accept_multiple_files=True)

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    baslat_btn = st.button("🚀 Analizi Başlat", type="primary", use_container_width=True)

if baslat_btn and yuklenen_dosyalar:
    standart_veriler = []
    raw_files_dict = {}
    with st.spinner("Dosyalar işleniyor, veri havuzu oluşturuluyor..."):
        for dosya in yuklenen_dosyalar:
            df_raw = banka_dosyasi_oku(dosya)
            if df_raw is not None:
                raw_files_dict[dosya.name] = df_raw
                st_df = veriyi_standartlastir(df_raw, dosya.name)
                if not st_df.empty: standart_veriler.append(st_df)

        if standart_veriler:
            st.session_state.raw_files = raw_files_dict
            st.session_state.ham_veriler = pd.concat(standart_veriler, ignore_index=True)
            st.session_state.tum_eslesmeler = virman_puanla_ve_bul(st.session_state.ham_veriler, st.session_state.dinamik_firma_kelimeleri, st.session_state.maks_gun_farki)
            
            # Hafızayı Sıfırla
            st.session_state.islenen_gidenler = set()
            st.session_state.islenen_gelenler = set()
            st.session_state.reddedilen_ciftler = set()
            st.session_state.onaylanan_silinecekler = []
            st.session_state.islem_gecmisi = []
            st.session_state.analiz_yapildi = True

if st.session_state.analiz_yapildi:
    # --- DİNAMİK HAVUZ SORGUSU ---
    kalan_adaylar = []
    for aday in st.session_state.tum_eslesmeler:
        g = aday['giden_index']
        c = aday['silinecek_index']
        if g in st.session_state.islenen_gidenler: continue
        if c in st.session_state.islenen_gelenler: continue
        if (g, c) in st.session_state.reddedilen_ciftler: continue
        kalan_adaylar.append(aday)
    # -----------------------------
    
    if len(kalan_adaylar) == 0:
        st.success(f"İnceleme tamamlandı. Olası tüm eşleşmeler sonuçlandırıldı! {len(st.session_state.onaylanan_silinecekler)} işlem mükerrer olarak işaretlendi.")
        
        silinen_dict = {}
        for idx in st.session_state.onaylanan_silinecekler:
            row = st.session_state.ham_veriler.iloc[idx]
            kaynak_dosya = row['KAYNAK']
            orijinal_satir = row['ORIJINAL_INDEX']
            if kaynak_dosya not in silinen_dict: silinen_dict[kaynak_dosya] = []
            silinen_dict[kaynak_dosya].append(orijinal_satir)

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            for dosya_adi, raw_df in st.session_state.raw_files.items():
                export_df = raw_df.copy()
                export_df = export_df.astype(str).replace(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', regex=True)
                export_df.insert(0, 'DURUM', '')
                silinecek_satirlar = silinen_dict.get(dosya_adi, [])
                export_df.loc[silinecek_satirlar, 'DURUM'] = 'SİLİNDİ'
                export_df.columns = ['DURUM'] + [f"Sütun {i+1}" for i in range(len(raw_df.columns))]
                
                def satir_boya(row): return ['background-color: #fef08a'] * len(row) if row.name in silinecek_satirlar else [''] * len(row)
                styled_df = export_df.style.apply(satir_boya, axis=1)
                styled_df.to_excel(writer, index=False, sheet_name="".join([c for c in dosya_adi if c not in r'\/*?:[]'])[:31])
        
        st.markdown("### 📊 İşlem İzleme Raporu")
        st.download_button(label="📉 Kontrol Raporunu İndir (Excel)", data=excel_buffer.getvalue(), file_name="Islem_Raporu.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.markdown("---\n### 📥 LUCA Dosyaları")
        
        temiz_df = st.session_state.ham_veriler.drop(index=st.session_state.onaylanan_silinecekler).reset_index(drop=True)
        banka_gruplari = temiz_df.groupby('KAYNAK')
        buton_kolonlari = st.columns(3)
        sayac = 0
        
        for dosya_adi, data in banka_gruplari:
            luca_df = pd.DataFrame()
            luca_df['TARİH'] = data['TARİH'] 
            luca_df['AÇIKLAMA'] = data['AÇIKLAMA']
            luca_df['TUTAR'] = data['TUTAR'].apply(lambda x: f"{x:.2f}".replace('.', ','))
            
            csv_buffer = io.BytesIO()
            luca_df.to_csv(csv_buffer, index=False, sep=';', encoding='cp1254') 
            with buton_kolonlari[sayac % 3]:
                st.download_button(label=f"📄 {dosya_adi[:15]}...", data=csv_buffer.getvalue(), file_name=f"LUCA_{dosya_adi.split('.')[0]}.csv", mime="text/csv")
            sayac += 1
            
    else:
        aday = kalan_adaylar[0] # Havuzdaki en yüksek puanlı sıradaki işlemi getir
        g_idx = aday['giden_index']
        c_idx = aday['silinecek_index']
        
        st.progress(0, text=f"Bekleyen Olası Eşleşme Sayısı: {len(kalan_adaylar)}")
        
        with st.container(border=True):
            st.markdown(f"#### ⚡ Eşleşme İhtimali: %{aday['Olasılık']}")
            st.caption(f"Bulgular: {aday['Nedeni']}")
            
            kart_col1, kart_col2 = st.columns(2)
            with kart_col1: st.info(f"**📤 ÇIKIŞ (Giden)**\n\n**Banka:** {aday['Giden_Banka']}\n\n**Tarih:** {aday['Giden_Tarih']}\n\n**Tutar:** {aday['Giden_Tutar']:,.2f} TL\n\n*{aday['Giden_Aciklama']}*")
            with kart_col2: st.success(f"**📥 GİRİŞ (Gelen)**\n\n**Banka:** {aday['Gelen_Banka']}\n\n**Tarih:** {aday['Gelen_Tarih']}\n\n**Tutar:** +{aday['Gelen_Tutar']:,.2f} TL\n\n*{aday['Gelen_Aciklama']}*")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- ANA AKSİYONLAR ---
            b_geri, b_atla, b_onayla = st.columns([1, 2, 2])
            with b_geri: st.button("⬅️ Geri Dön (W)", use_container_width=True, disabled=(len(st.session_state.islem_gecmisi) == 0), on_click=geri_al)
            with b_atla: st.button("🔄 Yanlış Eşleşme (A)", use_container_width=True, help="İki işlem de havuza döner.", on_click=aksiyon_al, args=('YANLIS_ESLESME', g_idx, c_idx))
            with b_onayla: st.button("✅ Onayla (D)", type="primary", use_container_width=True, help="Mükerrer kaydı sil.", on_click=aksiyon_al, args=('ONAYLA', g_idx, c_idx))
            
            # --- HAVUZ YÖNETİMİ AKSİYONLARI ---
            st.markdown("<br>", unsafe_allow_html=True)
            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1: st.button("🚫 Çıkış Virman Değil (1)", use_container_width=True, help="Çıkış çöpe atılır, Giriş havuza döner.", on_click=aksiyon_al, args=('GIDEN_DEGIL', g_idx, c_idx))
            with r_col2: st.button("🚫 Giriş Virman Değil (2)", use_container_width=True, help="Giriş çöpe atılır, Çıkış havuza döner.", on_click=aksiyon_al, args=('GELEN_DEGIL', g_idx, c_idx))
            with r_col3: st.button("🗑️ İkisi de Virman Değil (3)", use_container_width=True, help="İki işlem de çöpe atılır.", on_click=aksiyon_al, args=('IKISI_DE_DEGIL', g_idx, c_idx))