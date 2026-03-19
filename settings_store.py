import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_settings.json")

DEFAULT_SETTINGS = {
    "firma_girdisi": "",
    "dinamik_firma_kelimeleri": [],
    "maks_gun_farki": 4,
    "otomatik_onay_aktif": True,
    "otomatik_onay_esigi": 95,
    "toplu_onay_esigi": 90,
    "kullanici_haric_kelimeleri": [],
    "banka_hesap_kodlari": {},
}


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    payload = dict(DEFAULT_SETTINGS)
    payload.update(settings)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
