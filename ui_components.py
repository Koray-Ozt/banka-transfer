import streamlit as st

from settings_store import save_settings
from state import extract_settings_for_save


def apply_page_style():
    st.set_page_config(page_title="Virman Yönetimi", layout="wide", page_icon="🏦", initial_sidebar_state="collapsed")
    st.markdown(
        """
        <style>
        * { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; }
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}

        .hero {
            background: radial-gradient(circle at 20% 20%, #1d4ed8 0%, #0b1220 42%, #09101c 100%);
            color: #e2e8f0;
            padding: 26px 18px;
            margin: -1rem -1rem 1.2rem -1rem;
            border-radius: 0 0 16px 16px;
            border-bottom: 1px solid rgba(148,163,184,0.25);
        }
        .hero h1 { margin: 0; font-size: 26px; font-weight: 750; }
        .hero p { margin: 8px 0 0; color: #93c5fd; font-size: 13px; }

        .app-footer {
            position: fixed; left: 0; bottom: 0; width: 100%;
            background: linear-gradient(90deg, #0f172a, #1e293b);
            color: rgba(255,255,255,0.72); text-align: center;
            padding: 9px; font-size: 11px; z-index: 100; pointer-events: none;
        }

        .stat-card {
            background: #0f172a; padding: 16px 12px; border-radius: 12px;
            border: 1px solid rgba(148,163,184,0.16); text-align: center;
        }
        .stat-label { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }
        .stat-val { font-size: 24px; font-weight: 800; margin-top: 6px; }

        .panel {
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
            border-radius: 14px;
            padding: 22px;
            border: 1px solid rgba(148,163,184,0.14);
        }

        .reason-chip {
            display: inline-block; padding: 4px 10px; border-radius: 999px;
            font-size: 11px; font-weight: 600; margin: 3px;
            background: rgba(56,189,248,0.10); color: #7dd3fc;
            border: 1px solid rgba(56,189,248,0.24);
        }

        .txn-card {
            background: rgba(15,23,42,0.72); border-radius: 12px; padding: 16px;
            border: 1px solid rgba(148,163,184,0.12);
        }
        .txn-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
        .txn-row:not(:last-child) { border-bottom: 1px solid rgba(148,163,184,0.08); }
        .txn-lbl { font-size: 12px; color: #64748b; font-weight: 600; }
        .txn-val { font-size: 13px; color: #e2e8f0; font-weight: 500; text-align: right; }
        .txn-amount { font-size: 20px; font-weight: 800; }
        </style>
        <div class='app-footer'>Virman Yönetimi</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='hero'><h1>Virman ve Mükerrer Kayıt Yönetimi</h1><p>Dosyaları yükleyin, eşleşmeleri inceleyin, çıktıları alın.</p></div>", unsafe_allow_html=True)


def _save_settings_and_notice():
    save_settings(extract_settings_for_save())
    st.success("Ayarlar kaydedildi.")


def render_settings_panel():
    st.markdown("### Ayarlar")
    ayarlar_tab, filtre_tab, hesap_tab = st.tabs(["İşlem Parametreleri", "Kara Liste", "Banka Hesap Kodları"])

    with ayarlar_tab:
        with st.form("ayarlar_formu"):
            col_a, col_b = st.columns(2)
            with col_a:
                yeni_firma_girdisi = st.text_input(
                    "Firma Unvanı / Kısa Adı",
                    value=st.session_state.firma_girdisi,
                    placeholder="Örn: ABC A.Ş., XYZ Ticaret",
                )
            with col_b:
                yeni_maks_gun = st.slider("Valör Toleransı (Gün)", min_value=0, max_value=15, value=st.session_state.maks_gun_farki)

            col_c, col_d = st.columns(2)
            with col_c:
                yeni_otomatik_onay_aktif = st.checkbox("Yüksek güvenli eşleşmeleri otomatik onayla", value=st.session_state.otomatik_onay_aktif)
                yeni_otomatik_esik = st.slider("Otomatik Onay Eşiği (%)", min_value=70, max_value=100, value=st.session_state.otomatik_onay_esigi)
            with col_d:
                yeni_toplu_onay_esigi = st.slider("Toplu Onay Asgari Olasılık (%)", min_value=70, max_value=100, value=st.session_state.toplu_onay_esigi)

            if st.form_submit_button("Kaydet", use_container_width=True):
                st.session_state.firma_girdisi = yeni_firma_girdisi
                st.session_state.dinamik_firma_kelimeleri = [k.strip().upper() for k in yeni_firma_girdisi.split(",") if len(k.strip()) > 2]
                st.session_state.maks_gun_farki = yeni_maks_gun
                st.session_state.otomatik_onay_aktif = yeni_otomatik_onay_aktif
                st.session_state.otomatik_onay_esigi = yeni_otomatik_esik
                st.session_state.toplu_onay_esigi = yeni_toplu_onay_esigi
                _save_settings_and_notice()

    with filtre_tab:
        with st.form("kara_liste_formu"):
            yeni_haric_kelime_girdisi = st.text_area(
                "Virman Dışı Kelimeler",
                value=", ".join(st.session_state.kullanici_haric_kelimeleri),
                placeholder="Örn: MASRAF, POS, KOMİSYON",
                height=100,
            )
            if st.form_submit_button("Kaydet", use_container_width=True):
                st.session_state.kullanici_haric_kelimeleri = [k.strip().upper() for k in yeni_haric_kelime_girdisi.split(",") if len(k.strip()) > 2]
                _save_settings_and_notice()

    with hesap_tab:
        tum_bankalar = [
            "TEB",
            "GARANTİ",
            "ZİRAAT",
            "HALKBANK",
            "VAKIFBANK",
            "AKBANK",
            "YAPI KREDİ",
            "İŞ BANKASI",
            "QNB",
            "DENİZBANK",
            "KUVEYT TÜRK",
            "ALBARAKA",
            "ODEA",
            "FİBABANKA",
            "ŞEKERBANK",
            "ING",
            "PAPARA",
        ]
        with st.form("hesap_kodlari_formu"):
            hesap_kodlari_yeni = {}
            hesap_kolonlari = st.columns(3)
            for idx, banka_adi in enumerate(tum_bankalar):
                with hesap_kolonlari[idx % 3]:
                    kod = st.text_input(
                        f"{banka_adi}",
                        value=st.session_state.banka_hesap_kodlari.get(banka_adi, ""),
                        placeholder="Örn: 102.01.002",
                        key=f"hesap_kod_{banka_adi}",
                    )
                    if kod.strip():
                        hesap_kodlari_yeni[banka_adi] = kod.strip()
            if st.form_submit_button("Kaydet", use_container_width=True):
                st.session_state.banka_hesap_kodlari = hesap_kodlari_yeni
                _save_settings_and_notice()
