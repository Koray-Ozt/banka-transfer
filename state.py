import streamlit as st
from settings_store import load_settings


SETTINGS_KEYS = {
    "firma_girdisi",
    "dinamik_firma_kelimeleri",
    "maks_gun_farki",
    "otomatik_onay_aktif",
    "otomatik_onay_esigi",
    "toplu_onay_esigi",
    "kullanici_haric_kelimeleri",
    "banka_hesap_kodlari",
}


def init_state():
    base = {
        "analiz_yapildi": False,
        "ham_veriler": None,
        "raw_files": {},
        "tum_eslesmeler": [],
        "islenen_gidenler": set(),
        "islenen_gelenler": set(),
        "reddedilen_ciftler": set(),
        "onaylanan_silinecekler": [],
        "islem_gecmisi": [],
        "okuma_uyarilari": [],
        "otomatik_islenen_sayisi": 0,
    }
    for key, value in base.items():
        if key not in st.session_state:
            st.session_state[key] = value

    persisted = load_settings()
    for key, value in persisted.items():
        if key not in st.session_state:
            st.session_state[key] = value


def extract_settings_for_save():
    return {k: st.session_state.get(k) for k in SETTINGS_KEYS}
