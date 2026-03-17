import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import io
import re
import csv
import html as html_module

try:
    from charset_normalizer import from_bytes as detect_encoding
    CHARSET_NORMALIZER_AVAILABLE = True
except ImportError:
    CHARSET_NORMALIZER_AVAILABLE = False

# ==========================================
# 1. ARAYÜZ AYARLARI VE CSS (Masaüstü Tam Ekran)
# ==========================================
st.set_page_config(page_title="Akıllı Virman Yönetimi", layout="wide", page_icon="🏦", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    * { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    
    .app-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);
        color: white; padding: 28px 20px; margin: -1rem -1rem 1.5rem -1rem;
        border-radius: 0 0 16px 16px; text-align: center;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.3);
    }
    .app-header h1 { font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -0.5px; }
    .app-header p { font-size: 13px; color: rgba(255,255,255,0.7); margin: 6px 0 0 0; font-weight: 400; }
    
    .app-footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background: linear-gradient(90deg, #1e3a8a, #2563eb);
        color: rgba(255,255,255,0.8); text-align: center;
        padding: 10px; font-size: 11px; z-index: 100; pointer-events: none;
    }
    
    .stat-card {
        background: #1e293b; padding: 18px 14px; border-radius: 12px;
        border: 1px solid rgba(148,163,184,0.12);
        text-align: center; transition: transform 0.2s;
    }
    .stat-card:hover { transform: translateY(-2px); }
    .stat-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .stat-val { font-size: 26px; font-weight: 800; margin-top: 6px; }
    
    .match-panel {
        background: #1e293b; border-radius: 14px; padding: 24px;
        border: 1px solid rgba(148,163,184,0.1);
    }
    
    .pct-ring {
        width: 80px; height: 80px; border-radius: 50%; 
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; font-weight: 800; margin: 0 auto;
    }
    
    .reason-chip {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-size: 11px; font-weight: 600; margin: 3px;
        background: rgba(37,99,235,0.15); color: #60a5fa;
        border: 1px solid rgba(37,99,235,0.25);
    }
    
    .txn-card {
        background: #0f172a; border-radius: 12px; padding: 18px;
        border: 1px solid rgba(148,163,184,0.08);
    }
    .txn-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
    .txn-row:not(:last-child) { border-bottom: 1px solid rgba(148,163,184,0.06); }
    .txn-lbl { font-size: 12px; color: #64748b; font-weight: 600; }
    .txn-val { font-size: 13px; color: #e2e8f0; font-weight: 500; text-align: right; }
    .txn-amount { font-size: 20px; font-weight: 800; }
    
    .auto-banner {
        background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2);
        border-radius: 10px; padding: 12px 16px; margin-bottom: 16px;
        color: #6ee7b7; font-size: 13px;
    }
    .auto-banner strong { color: #34d399; }
    
    .stTabs [data-baseweb="tab-list"] { border-bottom: 1px solid rgba(148,163,184,0.15); }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #3b82f6 !important; color: #60a5fa !important; }
    </style>
    <div class="app-footer">🏦 Akıllı Virman Yönetimi | made with ❤️ by Koray Öztürk</div>
""", unsafe_allow_html=True)

st.markdown('<div class="app-header"><h1>💼 Mükerrer Kayıt ve Virman Yönetimi</h1><p>Dinamik Havuz Mimarisi &bull; Çoklu Seçenekli Eşleştirme Motoru &bull; Otomatik İşlem</p></div>', unsafe_allow_html=True)

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
if 'okuma_uyarilari' not in st.session_state: st.session_state.okuma_uyarilari = []
if 'otomatik_onay_aktif' not in st.session_state: st.session_state.otomatik_onay_aktif = True
if 'otomatik_onay_esigi' not in st.session_state: st.session_state.otomatik_onay_esigi = 95
if 'toplu_onay_esigi' not in st.session_state: st.session_state.toplu_onay_esigi = 90
if 'kullanici_haric_kelimeleri' not in st.session_state: st.session_state.kullanici_haric_kelimeleri = []
if 'otomatik_islenen_sayisi' not in st.session_state: st.session_state.otomatik_islenen_sayisi = 0

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
st.markdown("### ⚙️ Ayarlar & Yapılandırma")

ayarlar_tab, profil_tab = st.tabs(["🔧 İşlem Parametreleri", "🎯 Akıllı Filtreler"])

with ayarlar_tab:
    with st.form("ayarlar_formu"):
        st.markdown("**Virman Tespiti Ayarları**")
        col_a, col_b = st.columns(2)
        with col_a:
            yeni_firma_girdisi = st.text_input(
                "Firma Unvanı / Kısa Adı",
                value=st.session_state.firma_girdisi,
                placeholder="Örn: ABC A.Ş., XYZ Ticaret",
                help="Açıklamada aranacak firma adlarını virgülle ayırarak girin."
            )
        with col_b:
            yeni_maks_gun = st.slider(
                "Valör Toleransı (Gün)",
                min_value=0, max_value=15,
                value=st.session_state.maks_gun_farki,
                help="Giden ve gelen işlem arasında izin verilen günlük fark."
            )

        st.markdown("**Otomatik İşlem Ayarları**")
        col_c, col_d = st.columns(2)
        with col_c:
            yeni_otomatik_onay_aktif = st.checkbox(
                "🚀 Yüksek Güvenli Eşleşmeleri Otomatik Onayla",
                value=st.session_state.otomatik_onay_aktif,
                help="Puan, banka teyidi ve zaman uyumu şartlarını sağlayan eşleşmeleri otomatik temizle."
            )
            yeni_otomatik_esik = st.slider(
                "Otomatik Onay Eşiği (%)",
                min_value=70, max_value=100,
                value=st.session_state.otomatik_onay_esigi,
                help="Bu puanın üstündeki işlemler auto-approve kriteri kontrol edilecek."
            )
        with col_d:
            yeni_toplu_onay_esigi = st.slider(
                "Toplu Onay Asgari Olasılık (%)",
                min_value=70, max_value=100,
                value=st.session_state.toplu_onay_esigi,
                help="Aynı tutardaki işlemleri toplu onaylarken minimum puan."
            )

        ayarlari_kaydet = st.form_submit_button("💾 Ayarları Kaydet", use_container_width=True)
        
    if ayarlari_kaydet:
        st.session_state.firma_girdisi = yeni_firma_girdisi
        st.session_state.dinamik_firma_kelimeleri = [k.strip().upper() for k in yeni_firma_girdisi.split(',') if len(k.strip()) > 2]
        st.session_state.maks_gun_farki = yeni_maks_gun
        st.session_state.otomatik_onay_aktif = yeni_otomatik_onay_aktif
        st.session_state.otomatik_onay_esigi = yeni_otomatik_esik
        st.session_state.toplu_onay_esigi = yeni_toplu_onay_esigi
        st.success("✅ Ayarlar başarıyla kaydedildi!")

with profil_tab:
    with st.form("kara_liste_formu"):
        st.markdown("**Dinamik Kara Liste Yönetimi**")
        st.markdown("Sistem tarafından virman dışı işlem olarak işaretlenecek kelimeleri belirleyin.")
        yeni_haric_kelime_girdisi = st.text_area(
            "Dinamik Kara Liste Kelimeleri",
            value=", ".join(st.session_state.kullanici_haric_kelimeleri),
            placeholder="Örn: MASRAF, POS, KOMİSYON\nHer kelimeyi virgülle ayırın.",
            height=100,
            help="Açıklamada bu kelimeleri içeren işlemler virman adayı olmaktan çıkacaktır."
        )
        profil_kaydet = st.form_submit_button("💾 Kara Listeyi Güncelle", use_container_width=True)
    
    if profil_kaydet:
        st.session_state.kullanici_haric_kelimeleri = [k.strip().upper() for k in yeni_haric_kelime_girdisi.split(',') if len(k.strip()) > 2]
        st.success("✅ Kara liste başarıyla güncellendi!")

st.markdown("---")

# ==========================================
# 4. SIFIR VERİ KAYBI VE OKUMA MOTORU
# ==========================================
def banka_dosyasi_oku(dosya):
    veri_bytes = dosya.read()
    dosya.seek(0)
    hata_kayitlari = []
    dosya_adi = getattr(dosya, 'name', 'Bilinmeyen dosya')
    uzanti = dosya_adi.lower().rsplit('.', 1)[-1] if '.' in dosya_adi else ''
    excel_uzantisi = uzanti in {'xls', 'xlsx', 'xlsm', 'xlsb'}

    if excel_uzantisi:
        excel_engine = 'xlrd' if uzanti == 'xls' else None
        try:
            df = pd.read_excel(io.BytesIO(veri_bytes), header=None, engine=excel_engine)
            if len(df.columns) >= 3:
                return df.fillna('')
        except ImportError as exc:
            if uzanti == 'xls':
                hata_kayitlari.append("Excel okuma başarısız: .xls dosyaları için 'xlrd>=2.0.1' gerekli.")
            else:
                hata_kayitlari.append(f"Excel okuma başarısız: {exc}")
        except Exception as exc:
            hata_kayitlari.append(f"Excel okuma başarısız: {exc}")

        # Excel uzantılı dosya parse edilemediyse ikili içeriği HTML/CSV gibi okumaya zorlamayız.
        if hata_kayitlari:
            st.session_state.okuma_uyarilari.append(f"{dosya_adi}: {' | '.join(hata_kayitlari)}")
        return None

    try:
        dfs = pd.read_html(io.BytesIO(veri_bytes))
        if dfs and len(dfs) > 0:
            dfs.sort(key=lambda x: len(x), reverse=True)
            return dfs[0].fillna('')
    except Exception as exc:
        hata_kayitlari.append(f"HTML okuma başarısız: {exc}")
    metin = ""
    if CHARSET_NORMALIZER_AVAILABLE:
        sonuc = detect_encoding(veri_bytes)
        en_iyi = sonuc.best()
        if en_iyi is not None:
            metin = str(en_iyi)
    if not metin:
        for enc in ['utf-8', 'cp1254', 'ISO-8859-9']:
            try:
                metin = veri_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    if not metin:
        metin = veri_bytes.decode('utf-8', errors='ignore')
    satirlar = metin.splitlines()
    noktali_virgul = sum(s.count(';') for s in satirlar[:50])
    virgul = sum(s.count(',') for s in satirlar[:50])
    tab_sayisi = sum(s.count('\t') for s in satirlar[:50])
    ayrac = '\t' if (tab_sayisi > noktali_virgul and tab_sayisi > virgul) else (';' if noktali_virgul > virgul else ',')
    reader = csv.reader(io.StringIO(metin), delimiter=ayrac)
    try:
        return pd.DataFrame(list(reader)).fillna('')
    except Exception as exc:
        hata_kayitlari.append(f"CSV okuma başarısız: {exc}")

    if hata_kayitlari:
        st.session_state.okuma_uyarilari.append(f"{dosya_adi}: {' | '.join(hata_kayitlari)}")
    return None

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
    except (ValueError, TypeError): return 0.0

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
    tum_haric_kelimeler = list(dict.fromkeys(haric_kelimeler + st.session_state.kullanici_haric_kelimeleri))
    if tum_haric_kelimeler:
        haric_regex = '|'.join(re.escape(k) for k in tum_haric_kelimeler)
        st_df.loc[st_df['AÇIKLAMA'].astype(str).str.upper().str.contains(haric_regex, regex=True, na=False), 'VIRMAN_ADAYI'] = False
    ticari_regex = r'(ALT[Iİ]N|ALTI|ALTN).{0,5}(AL[Iİ]M|BEDEL[Iİ])|AL[Iİ]M.{0,5}BEDEL[Iİ]|ELDEN.{0,5}TESL[Iİ]M|TESL[Iİ]M.{0,5}ALD[Iİ]M'
    st_df.loc[st_df['AÇIKLAMA'].astype(str).str.upper().str.contains(ticari_regex, regex=True, na=False), 'VIRMAN_ADAYI'] = False
    return st_df.reset_index(drop=True)

# ==========================================
# 5. BANKA DEDEKTİFİ & TÜM OLASILIKLARI BULMA
# ==========================================
def banka_bul(metin):
    metin = str(metin).upper()
    bulunanlar = []
    bulunan_seti = set()

    def banka_ekle(banka_adi):
        if banka_adi not in bulunan_seti:
            bulunan_seti.add(banka_adi)
            bulunanlar.append(banka_adi)

    kisa_kodlar = {'TEB': r'\bTEB\b', 'QNB': r'\bQNB\b', 'YAPI KREDİ': r'\bYKB\b', 'ING': r'\bİ?NG\b', 'HALKBANK': r'\bHALK\b', 'VAKIFBANK': r'\bVAKIF\b'}
    for banka, desen in kisa_kodlar.items():
        if re.search(desen, metin):
            banka_ekle(banka)
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
        if any(k in metin for k in kelimeler):
            banka_ekle(banka_adi)
    return bulunanlar

KELIME_DESENI = re.compile(r'[A-ZĞÜŞİÖÇ0-9]{3,}')

def virman_puanla_ve_bul(df, sirket_kelimeleri, maks_gun):
    df = df.reset_index(drop=True)
    adaylar_df = df[df['VIRMAN_ADAYI'] == True].copy()
    if adaylar_df.empty:
        return []

    # Float hassasiyet kaynaklı grup kaçırmalarını önlemek için kuruş bazında eşleştiriyoruz.
    adaylar_df['MUTLAK_TUTAR_KURUS'] = (adaylar_df['TUTAR'].abs().round(2) * 100).astype('int64')
    adaylar_df['TARIH_OBJ'] = pd.to_datetime(adaylar_df['TARİH'], format='%d.%m.%Y', errors='coerce')
    adaylar_df = adaylar_df.dropna(subset=['TARIH_OBJ']).copy()
    if adaylar_df.empty:
        return []

    adaylar_df['ACIKLAMA_UPPER'] = adaylar_df['AÇIKLAMA'].astype(str).str.upper()
    jenerikler = {'İLE', 'İÇİN', 'BANK', 'BANKASI', 'ŞUBESİ', 'HAVALE', 'GÖNDEREN', 'ALICI', 'İŞLEMLERİ', 'BEDELİ', 'ELDEN', 'TESLİM', 'ALDIM', 'NOLU', 'GİDEN', 'GELEN', 'ÖDEME', 'ÖDEMESİ', 'HESABA', 'HESAPTAN', 'FAST', 'EFT', 'SWIFT', 'İBAN', 'IBAN', 'SANAYİ', 'TİCARET', 'KUYUMCULUK', 'ALTIN', 'ALIMI', 'ALIM', 'SATIM', 'SATIŞ', 'A.Ş.', 'A.S.', 'LTD.', 'ŞTİ.', 'LİMİTED', 'ŞİRKETİ', 'SORG', 'NO', 'TÜRK', 'A.S', 'A.Ş'}
    adaylar_df['KELIMELER'] = adaylar_df['ACIKLAMA_UPPER'].apply(lambda aciklama: {w for w in KELIME_DESENI.findall(aciklama) if w not in jenerikler})
    adaylar_df['ACIKLAMA_BANKALARI'] = adaylar_df['AÇIKLAMA'].apply(banka_bul)
    grup = adaylar_df.groupby('MUTLAK_TUTAR_KURUS')
    
    tum_eslesmeler = []
    dosya_bankalari = {}
    for dosya_adi in df['KAYNAK'].unique():
        bulunan_bankalar = banka_bul(dosya_adi)
        dosya_bankalari[dosya_adi] = bulunan_bankalar[0] if bulunan_bankalar else None

    kesin_virman_kelimeleri = ['VİRMAN', 'VIRMAN', 'KENDİ', 'KENDI', 'TRANSFER', 'MAHSUP'] + sirket_kelimeleri
    
    for tutar_kurus, data in grup:
        if len(data) > 1:
            artilar = data[data['TUTAR'] > 0] 
            eksiler = data[data['TUTAR'] < 0] 
            if not artilar.empty and not eksiler.empty:
                for i, arti in artilar.iterrows():
                    kelimeler_gelen = arti['KELIMELER']
                    tarih_arti = arti['TARIH_OBJ']
                    gelen_gercek_banka = dosya_bankalari.get(arti['KAYNAK'])
                    gelen_aciklama_bankalari = arti['ACIKLAMA_BANKALARI']

                    uygun_eksiler = eksiler[(eksiler['TARIH_OBJ'] >= tarih_arti - pd.Timedelta(days=maks_gun)) & (eksiler['TARIH_OBJ'] <= tarih_arti + pd.Timedelta(days=maks_gun))]
                    if uygun_eksiler.empty:
                        continue
                    
                    for j, eksi in uygun_eksiler.iterrows():
                        tarih_eksi = eksi['TARIH_OBJ']
                        gun_farki_gercek = abs((tarih_arti - tarih_eksi).days)
                            
                        dakika_farki_gercek = 0
                        if (arti['SAAT'] != '00:00' and eksi['SAAT'] != '00:00' and pd.notna(arti['TARIH_SAAT_OBJ']) and pd.notna(eksi['TARIH_SAAT_OBJ'])):
                            dakika_farki_gercek = abs((arti['TARIH_SAAT_OBJ'] - eksi['TARIH_SAAT_OBJ']).total_seconds() / 60)
                                
                        giden_gercek_banka = dosya_bankalari.get(eksi['KAYNAK'])
                        giden_aciklama_bankalari = eksi['ACIKLAMA_BANKALARI']
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
                            
                        kelimeler_giden = eksi['KELIMELER']
                        ortak_kelimeler = kelimeler_giden.intersection(kelimeler_gelen)
                        if ortak_kelimeler: puan += 30; nedenler.append(f"Ortak Terim")
                            
                        if puan >= 55:
                            tum_eslesmeler.append({
                                'Olasılık': min(puan, 100), 'Tutar': round(tutar_kurus / 100, 2), 
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

def aday_islenebilir_mi(giden_idx, gelen_idx):
    if giden_idx in st.session_state.islenen_gidenler:
        return False
    if gelen_idx in st.session_state.islenen_gelenler:
        return False
    if (giden_idx, gelen_idx) in st.session_state.reddedilen_ciftler:
        return False
    return True

def onayli_cifti_isaretle(giden_idx, gelen_idx):
    st.session_state.islenen_gidenler.add(giden_idx)
    st.session_state.islenen_gelenler.add(gelen_idx)
    if gelen_idx not in st.session_state.onaylanan_silinecekler:
        st.session_state.onaylanan_silinecekler.append(gelen_idx)

def otomatik_onay_kriteri(aday, esik):
    neden = str(aday.get('Nedeni', ''))
    if aday.get('Olasılık', 0) < esik:
        return False
    if 'Banka Teyidi' not in neden:
        return False
    return any(k in neden for k in ['Saat Eşleşmesi', 'Yakın Saat', 'Aynı Gün'])

def toplu_onayla_ayni_tutar(hedef_tutar, min_olasilik):
    gecmisi_kaydet()
    adet = 0
    hedef = round(float(hedef_tutar), 2)
    for aday in st.session_state.tum_eslesmeler:
        g = aday['giden_index']
        c = aday['silinecek_index']
        if not aday_islenebilir_mi(g, c):
            continue
        if round(float(aday.get('Tutar', 0)), 2) != hedef:
            continue
        if aday.get('Olasılık', 0) < min_olasilik:
            continue
        onayli_cifti_isaretle(g, c)
        adet += 1
    return adet

def aksiyon_al(aksiyon_tipi, giden_idx, gelen_idx, kaydet_gecmis=True):
    if kaydet_gecmis:
        gecmisi_kaydet()
    if aksiyon_tipi == 'ONAYLA':
        onayli_cifti_isaretle(giden_idx, gelen_idx)
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
st.markdown("### 📁 Veri Yükle ve Analiz Et")
st.markdown("CSV, XLS, XLSX formatında banka ekstrelerini yükleyip analizi başlatın.")

yuklenen_dosyalar = st.file_uploader(
    "İşlenecek Ekstreleri Yükleyin",
    type=["csv", "xls", "xlsx"],
    accept_multiple_files=True,
    help="Desteklenen formatlar: .csv, .xls, .xlsx | Birden fazla dosya seçebilirsiniz."
)

if yuklenen_dosyalar:
    st.markdown(f"**📦 {len(yuklenen_dosyalar)} dosya seçildi**")
    for f in yuklenen_dosyalar:
        st.caption(f"✓ {f.name} ({f.size/1024:.1f} KB)")

col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
with col_btn2:
    baslat_btn = st.button("🚀 Analizi Başlat", type="primary", use_container_width=True)

if baslat_btn and yuklenen_dosyalar:
    standart_veriler = []
    raw_files_dict = {}
    st.session_state.okuma_uyarilari = []
    st.session_state.otomatik_islenen_sayisi = 0
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
        else:
            st.session_state.analiz_yapildi = False
            st.error("📄 Yüklenen dosyalardan analiz edilebilir standart veri çıkarılamadı. Dosya biçimlerini ve kodlamalarını lütfen kontrol edin.")

    if st.session_state.okuma_uyarilari:
        with st.expander(f"⚠️ Okuma Uyarıları ({len(st.session_state.okuma_uyarilari)})", expanded=False):
            for uyari in st.session_state.okuma_uyarilari:
                st.warning(f"⚠️ {uyari}")
elif baslat_btn and not yuklenen_dosyalar:
    st.error("📄 Lütfen analizi başlatmadan önce en az bir ekstre dosyası yüklediğinizden eğlenin.")

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

    if st.session_state.otomatik_onay_aktif and kalan_adaylar:
        otomatik_adet = 0
        for aday in kalan_adaylar:
            if not otomatik_onay_kriteri(aday, st.session_state.otomatik_onay_esigi):
                continue
            g = aday['giden_index']
            c = aday['silinecek_index']
            if not aday_islenebilir_mi(g, c):
                continue
            aksiyon_al('ONAYLA', g, c, kaydet_gecmis=False)
            otomatik_adet += 1

        if otomatik_adet > 0:
            st.session_state.otomatik_islenen_sayisi += otomatik_adet
            st.markdown(f"<div class='auto-banner'><strong>✨ Otomatik İşlem</strong> — {otomatik_adet} yüksek güvenli eşleşme otomatik olarak onaylandı.</div>", unsafe_allow_html=True)
            st.rerun()

    toplam_kayit = 0 if st.session_state.ham_veriler is None else len(st.session_state.ham_veriler)
    toplam_aday = len(st.session_state.tum_eslesmeler)
    kalan_sayi = len(kalan_adaylar)
    onaylanan_sayi = len(st.session_state.onaylanan_silinecekler)
    reddedilen_sayi = len(st.session_state.reddedilen_ciftler)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Toplam Kayıt</div><div class='stat-val' style='color:#60a5fa;'>{toplam_kayit}</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Aday Eşleşme</div><div class='stat-val' style='color:#c084fc;'>{toplam_aday}</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Onaylanan</div><div class='stat-val' style='color:#34d399;'>{onaylanan_sayi}</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Reddedilen</div><div class='stat-val' style='color:#f87171;'>{reddedilen_sayi}</div></div>", unsafe_allow_html=True)
    with m5:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Oto. Onay</div><div class='stat-val' style='color:#2dd4bf;'>{st.session_state.otomatik_islenen_sayisi}</div></div>", unsafe_allow_html=True)
    
    progress_yuzde = 0 if toplam_aday == 0 else int((onaylanan_sayi + reddedilen_sayi) / toplam_aday * 100)
    st.caption(f"İşlem İlerleme: {progress_yuzde}%  •  Bekleyen: {kalan_sayi} aday")
    
    if len(kalan_adaylar) == 0:
        st.markdown(f"### ✅ İnceleme Tamamlandı!")
        st.success(f"🌟 {len(st.session_state.onaylanan_silinecekler)} mükerrer işlem başarıyla işaretlendi ve sistem tarafından temizlendi.")
        
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
        st.markdown("📕 Yüklenen dosyaların orijinal formatı korumakıyla birlikte, silinmesi gereken işlemler işaretlendi. Excel raporu ile revizyon yapabilirsiniz.")
        st.download_button(
            label="📉 Kontrol Raporunu İndir (Excel)",
            data=excel_buffer.getvalue(),
            file_name="Islem_Raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        st.markdown("---")
        st.markdown("### 📥 Mükerrer İşlemler Çıkarılmış LUCA Dosyaları")
        st.markdown("📑 Aşağıdaki dosyaları muhasebe sisteminize aktarabilirsiniz. Reddedilen ve silinen işlemler kaldırılmıştır.")
        
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
                st.download_button(
                    label=f"📄 {dosya_adi[:20]}...",
                    data=csv_buffer.getvalue(),
                    file_name=f"LUCA_{dosya_adi.split('.')[0]}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            sayac += 1
            
    else:
        aday = kalan_adaylar[0] # Havuzdaki en yüksek puanlı sıradaki işlemi getir
        g_idx = aday['giden_index']
        c_idx = aday['silinecek_index']
        
        toplam_aday = len(st.session_state.tum_eslesmeler)
        tamamlanan_aday = max(0, toplam_aday - len(kalan_adaylar))
        ilerleme_orani = 0.0 if toplam_aday == 0 else min(1.0, tamamlanan_aday / toplam_aday)
        st.progress(ilerleme_orani, text=f"Bekleyen Olası Eşleşme Sayısı: {len(kalan_adaylar)}")
        
        # --- EŞLEŞME PANELİ ---
        confidence_color = "#34d399" if aday['Olasılık'] >= 90 else "#fbbf24" if aday['Olasılık'] >= 75 else "#f87171"
        nedenler = [r.strip() for r in aday['Nedeni'].split('+')]
        neden_html = ''.join(f"<span class='reason-chip'>✓ {n}</span>" for n in nedenler)
        
        giden_aciklama_safe = html_module.escape(str(aday['Giden_Aciklama']))
        gelen_aciklama_safe = html_module.escape(str(aday['Gelen_Aciklama']))
        giden_banka_safe = html_module.escape(str(aday['Giden_Banka']))
        gelen_banka_safe = html_module.escape(str(aday['Gelen_Banka']))
        giden_tarih_safe = html_module.escape(str(aday['Giden_Tarih']))
        gelen_tarih_safe = html_module.escape(str(aday['Gelen_Tarih']))
        
        giden_html = f"""
        <div class='txn-card' style='border-top: 3px solid #f87171;'>
            <div style='font-weight:700; color:#f87171; font-size:14px; margin-bottom:12px;'>📤 ÇIKIŞ (Giden)</div>
            <div class='txn-row'><span class='txn-lbl'>Banka</span><span class='txn-val'>{giden_banka_safe}</span></div>
            <div class='txn-row'><span class='txn-lbl'>Tarih</span><span class='txn-val'>{giden_tarih_safe}</span></div>
            <div class='txn-row'><span class='txn-lbl'>Tutar</span><span class='txn-amount' style='color:#f87171;'>{aday['Giden_Tutar']:,.2f} ₺</span></div>
            <div style='margin-top:10px; padding-top:10px; border-top:1px solid rgba(148,163,184,0.08);'>
                <span class='txn-lbl'>Açıklama</span>
                <div style='color:#cbd5e1; font-size:12px; margin-top:4px; line-height:1.5;'>{giden_aciklama_safe}</div>
            </div>
        </div>"""
        
        gelen_html = f"""
        <div class='txn-card' style='border-top: 3px solid #34d399;'>
            <div style='font-weight:700; color:#34d399; font-size:14px; margin-bottom:12px;'>📥 GİRİŞ (Gelen)</div>
            <div class='txn-row'><span class='txn-lbl'>Banka</span><span class='txn-val'>{gelen_banka_safe}</span></div>
            <div class='txn-row'><span class='txn-lbl'>Tarih</span><span class='txn-val'>{gelen_tarih_safe}</span></div>
            <div class='txn-row'><span class='txn-lbl'>Tutar</span><span class='txn-amount' style='color:#34d399;'>+{aday['Gelen_Tutar']:,.2f} ₺</span></div>
            <div style='margin-top:10px; padding-top:10px; border-top:1px solid rgba(148,163,184,0.08);'>
                <span class='txn-lbl'>Açıklama</span>
                <div style='color:#cbd5e1; font-size:12px; margin-top:4px; line-height:1.5;'>{gelen_aciklama_safe}</div>
            </div>
        </div>"""
        
        st.markdown(f"""
        <div class='match-panel'>
            <div style='display:flex; align-items:center; gap:20px; margin-bottom:20px; flex-wrap:wrap;'>
                <div class='pct-ring' style='background:rgba(0,0,0,0.3); border:3px solid {confidence_color}; color:{confidence_color};'>%{aday['Olasılık']}</div>
                <div style='flex:1;'>
                    <div style='color:#94a3b8; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;'>Tespit Nedenleri</div>
                    {neden_html}
                </div>
            </div>
            <div style='display:grid; grid-template-columns:1fr 1fr; gap:14px;'>
                {giden_html}
                {gelen_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- ANA AKSİYONLAR ---
        b_geri, b_atla, b_onayla, b_toplu = st.columns([1, 2, 2, 3])
        with b_geri: st.button("⬅️ Geri Dön (W)", use_container_width=True, disabled=(len(st.session_state.islem_gecmisi) == 0), on_click=geri_al)
        with b_atla: st.button("🔄 Yanlış Eşleşme (A)", use_container_width=True, help="İki işlem de havuza döner.", on_click=aksiyon_al, args=('YANLIS_ESLESME', g_idx, c_idx))
        with b_onayla: st.button("✅ Onayla (D)", type="primary", use_container_width=True, help="Mükerrer kaydı sil.", on_click=aksiyon_al, args=('ONAYLA', g_idx, c_idx))
        with b_toplu:
            toplu_basildi = st.button(
                f"🧩 Aynı Tutarı Toplu Onayla (≥%{st.session_state.toplu_onay_esigi})",
                use_container_width=True,
                help="Mevcut adayla aynı tutardaki yüksek olasılıklı eşleşmeleri tek seferde onaylar."
            )
            if toplu_basildi:
                toplu_adet = toplu_onayla_ayni_tutar(aday['Tutar'], st.session_state.toplu_onay_esigi)
                st.success(f"Toplu işlem tamamlandı: {toplu_adet} eşleşme onaylandı.")
                st.rerun()
        
        # --- HAVUZ YÖNETİMİ AKSİYONLARI ---
        r_col1, r_col2, r_col3 = st.columns(3)
        with r_col1: st.button("🚫 Çıkış Virman Değil (1)", use_container_width=True, help="Çıkış çöpe atılır, Giriş havuza döner.", on_click=aksiyon_al, args=('GIDEN_DEGIL', g_idx, c_idx))
        with r_col2: st.button("🚫 Giriş Virman Değil (2)", use_container_width=True, help="Giriş çöpe atılır, Çıkış havuza döner.", on_click=aksiyon_al, args=('GELEN_DEGIL', g_idx, c_idx))
        with r_col3: st.button("🗑️ İkisi de Virman Değil (3)", use_container_width=True, help="İki işlem de çöpe atılır.", on_click=aksiyon_al, args=('IKISI_DE_DEGIL', g_idx, c_idx))