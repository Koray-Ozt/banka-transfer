import csv
import io
import os
import re

import numpy as np
import pandas as pd
import streamlit as st

try:
    from charset_normalizer import from_bytes as detect_encoding

    CHARSET_NORMALIZER_AVAILABLE = True
except ImportError:
    CHARSET_NORMALIZER_AVAILABLE = False


CSV_KLASORU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "banka csv")


def banka_dosyasi_oku(dosya):
    hata_kayitlari = []
    if isinstance(dosya, str):
        dosya_adi = os.path.basename(dosya)
        try:
            with open(dosya, "rb") as f:
                veri_bytes = f.read()
        except Exception as exc:
            st.session_state.okuma_uyarilari.append(f"{dosya_adi}: Dosya okunamadı: {exc}")
            return None
    else:
        dosya_adi = getattr(dosya, "name", "Bilinmeyen dosya")
        veri_bytes = dosya.read()
        dosya.seek(0)

    metin = ""
    try:
        metin = veri_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            metin = veri_bytes.decode("cp1254")
        except UnicodeDecodeError:
            if CHARSET_NORMALIZER_AVAILABLE:
                sonuc = detect_encoding(veri_bytes)
                en_iyi = sonuc.best()
                if en_iyi is not None:
                    metin = str(en_iyi)
            if not metin:
                for enc in ["cp1252", "ISO-8859-9"]:
                    try:
                        metin = veri_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
    if not metin:
        metin = veri_bytes.decode("utf-8", errors="ignore")

    metin = metin.lstrip("\ufeff")
    satirlar = metin.splitlines()
    noktali_virgul = sum(s.count(";") for s in satirlar[:50])
    virgul = sum(s.count(",") for s in satirlar[:50])
    tab_sayisi = sum(s.count("\t") for s in satirlar[:50])
    ayrac = "\t" if (tab_sayisi > noktali_virgul and tab_sayisi > virgul) else (";" if noktali_virgul > virgul else ",")

    reader = csv.reader(io.StringIO(metin), delimiter=ayrac)
    try:
        return pd.DataFrame(list(reader)).fillna("")
    except Exception as exc:
        hata_kayitlari.append(f"CSV okuma başarısız: {exc}")

    if hata_kayitlari:
        st.session_state.okuma_uyarilari.append(f"{dosya_adi}: {' | '.join(hata_kayitlari)}")
    return None


def tutar_temizle(deger):
    if pd.isna(deger) or str(deger).strip() == "":
        return 0.0
    deger_str = str(deger).upper().replace("TL", "").replace(" ", "").strip()
    if not deger_str or deger_str == "NAN":
        return 0.0

    carpan = -1 if deger_str.startswith("-") or deger_str.endswith("-") else 1
    deger_str = deger_str.replace("-", "")

    if "," in deger_str and "." in deger_str:
        if deger_str.rfind(",") > deger_str.rfind("."):
            deger_str = deger_str.replace(".", "").replace(",", ".")
        else:
            deger_str = deger_str.replace(",", "")
    elif "," in deger_str:
        deger_str = deger_str.replace(",", ".")

    try:
        return float(deger_str) * carpan
    except (ValueError, TypeError):
        return 0.0


def baslik_satirini_bul(df):
    for i in range(min(50, len(df))):
        satir_str = " ".join([str(x).upper() for x in df.iloc[i].values])
        if any(k in satir_str for k in ["TARİH", "TARIH", "TAR]H", "]~LEM", "DATE", "ZAMAN", "MUHTAR"]) and any(
            k in satir_str for k in ["TUTAR", "BORC", "BORÇ", "BORG", "ALACAK", "MEBLA"]
        ):
            return i
    return 0


def veriyi_standartlastir(df_raw, dosya_adi):
    baslik_idx = baslik_satirini_bul(df_raw)
    df = df_raw.iloc[baslik_idx + 1 :].copy()
    orijinal_indexler = df.index.values
    df = df.reset_index(drop=True)

    orijinal_kolonlar = (
        df_raw.iloc[baslik_idx]
        .astype(str)
        .str.upper()
        .str.replace(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", regex=True)
        .str.strip()
        .tolist()
    )
    df.columns = [f"{col}_{i}" if orijinal_kolonlar.count(col) > 1 or not col else col for i, col in enumerate(orijinal_kolonlar)]
    df = df.astype(str).replace(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", regex=True)

    st_df = pd.DataFrame()
    st_df["KAYNAK"] = [dosya_adi] * len(df)
    st_df["ORIJINAL_INDEX"] = orijinal_indexler

    tarih_kolonu = next(
        (
            c
            for c in df.columns
            if any(k in c for k in ["TARİH", "TARIH", "TAR]H", "TARIHI", "HAREKETISLEMTARIHI", "MUH TARİH"])
        ),
        None,
    )
    if not tarih_kolonu:
        return pd.DataFrame()

    df["GECICI_TARIH"] = df[tarih_kolonu].astype(str).str.extract(r"(\d{2,4}[./-]\d{2}[./-]\d{2,4})")[0]
    df["GECICI_TARIH"] = df["GECICI_TARIH"].fillna(df[tarih_kolonu].astype(str))
    st_df["TARİH"] = pd.to_datetime(df["GECICI_TARIH"], errors="coerce", dayfirst=True).dt.strftime("%d.%m.%Y")

    saat_kolonu = next((c for c in df.columns if any(k in c for k in ["SAAT", "ZAMAN"])), None)
    if saat_kolonu:
        saat_df = df[saat_kolonu].astype(str).str.extract(r"([01]?[0-9]|2[0-3])[:.]([0-5][0-9])")
    else:
        saat_df = df[tarih_kolonu].astype(str).str.extract(r"(?:\s|-|T)([01]?[0-9]|2[0-3])[:.]([0-5][0-9])")

    st_df["SAAT"] = np.where(saat_df[0].notna(), saat_df[0] + ":" + saat_df[1], "")
    st_df["SAAT_BILINIYOR"] = st_df["SAAT"].astype(str).str.match(r"^\d{1,2}:\d{2}$", na=False)

    zaman_str = np.where(st_df["SAAT_BILINIYOR"], st_df["TARİH"] + " " + st_df["SAAT"], st_df["TARİH"] + " 00:00")
    st_df["TARIH_SAAT_OBJ"] = pd.to_datetime(zaman_str, format="%d.%m.%Y %H:%M", errors="coerce")

    aciklama_kolonu = None
    for k in ["AÇIKLAMA", "ACIKLAMA", "AGIKLAMA", "AG}KLAMA", "AÇIKLAMAS", "FISACIKLAMA", "DETAY", "REFERANS"]:
        bulunan = [c for c in df.columns if k in c]
        if bulunan:
            aciklama_kolonu = bulunan[0]
            break
    st_df["AÇIKLAMA"] = df[aciklama_kolonu] if aciklama_kolonu else ""

    tutar_kolonu = next((c for c in df.columns if any(k in c for k in ["TUTAR", "MEBLA", "HAREKETTUTAR"])), None)
    ba_kolonu = next((c for c in df.columns if any(k in c for k in ["B/A", "BORCALACAK", "BORÇ/ALACAK", "BORG/ALACAK"])), None)
    borc_kolonu = next(
        (c for c in df.columns if any(k in c for k in ["BORÇ", "BORC", "BORG"]) and "ALACAK" not in c and "/" not in c),
        None,
    )
    alacak_kolonu = next((c for c in df.columns if "ALACAK" in c and "BORC" not in c and "/" not in c), None)

    if borc_kolonu and alacak_kolonu:
        st_df["TUTAR"] = df[alacak_kolonu].apply(tutar_temizle) - df[borc_kolonu].apply(tutar_temizle)
    elif tutar_kolonu and ba_kolonu:
        is_borc = df[ba_kolonu].astype(str).str.upper().str.startswith("B")
        st_df["TUTAR"] = np.where(is_borc, -df[tutar_kolonu].apply(tutar_temizle).abs(), df[tutar_kolonu].apply(tutar_temizle).abs())
    elif tutar_kolonu:
        st_df["TUTAR"] = df[tutar_kolonu].apply(tutar_temizle)
    else:
        return pd.DataFrame()

    bakiye_kolonu = next((c for c in df.columns if any(k in c for k in ["BAKİYE", "BAKIYE", "BAK]YE", "BAK}YE"])), None)
    st_df["BAKİYE"] = df[bakiye_kolonu].apply(tutar_temizle) if bakiye_kolonu else np.nan

    st_df = st_df.dropna(subset=["TARİH"]).reset_index(drop=True)
    st_df = st_df[st_df["TUTAR"] != 0].reset_index(drop=True)
    st_df["SIRA_NO"] = st_df["TARIH_SAAT_OBJ"].rank(method="first", ascending=True, na_option="bottom").astype(int) - 1

    st_df["VIRMAN_ADAYI"] = True
    haric_kelimeler = [
        "GİDER PUSULAS",
        "GIDER PUSULAS",
        "BSMV",
        "MASRAF",
        "KOMİSYON",
        "KOMISYON",
        "KOM.",
        "ÜCRET",
        "UCRET",
        "KDV",
        "VERGİ",
        "VERGI",
        "STOPAJ",
        "FAİZ",
        "FAIZ",
        "PŞNSTŞ",
        "PSNSTS",
        "POS ",
        "TAKAS",
        "İŞLETİM",
        "ISLETIM",
        "HİZMET",
        "HIZMET",
        "KESİNTİ",
        "KESINTI",
        "KART TAHSİLAT",
        "VERGİSİ",
    ]
    tum_haric_kelimeler = list(dict.fromkeys(haric_kelimeler + st.session_state.kullanici_haric_kelimeleri))
    if tum_haric_kelimeler:
        haric_regex = "|".join(re.escape(k) for k in tum_haric_kelimeler)
        st_df.loc[st_df["AÇIKLAMA"].astype(str).str.upper().str.contains(haric_regex, regex=True, na=False), "VIRMAN_ADAYI"] = False

    ticari_regex = r"(?:ALT[Iİ]N|ALTI|ALTN).{0,5}(?:AL[Iİ]M|BEDEL[Iİ])|AL[Iİ]M.{0,5}BEDEL[Iİ]|ELDEN.{0,5}TESL[Iİ]M|TESL[Iİ]M.{0,5}ALD[Iİ]M"
    st_df.loc[st_df["AÇIKLAMA"].astype(str).str.upper().str.contains(ticari_regex, regex=True, na=False), "VIRMAN_ADAYI"] = False
    return st_df.reset_index(drop=True)
