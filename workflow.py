import streamlit as st
import pandas as pd


def gecmisi_kaydet():
    st.session_state.islem_gecmisi.append(
        {
            "gidenler": set(st.session_state.islenen_gidenler),
            "gelenler": set(st.session_state.islenen_gelenler),
            "reddedilen": set(st.session_state.reddedilen_ciftler),
            "silinenler": list(st.session_state.onaylanan_silinecekler),
        }
    )


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
    neden = str(aday.get("Nedeni", ""))
    if aday.get("Olasılık", 0) < esik:
        return False
    if "Banka Teyidi" not in neden:
        return False
    return any(k in neden for k in ["Saat Yakın", "Saat Farkı", "Aynı Gün"])


def toplu_onayla_ayni_tutar(hedef_tutar, min_olasilik):
    gecmisi_kaydet()
    adet = 0
    hedef = round(float(hedef_tutar), 2)
    for aday in st.session_state.tum_eslesmeler:
        g = aday["giden_index"]
        c = aday["silinecek_index"]
        if not aday_islenebilir_mi(g, c):
            continue
        if round(float(aday.get("Tutar", 0)), 2) != hedef:
            continue
        if aday.get("Olasılık", 0) < min_olasilik:
            continue
        onayli_cifti_isaretle(g, c)
        adet += 1
    return adet


def toplu_onayla_banka_cifti(hedef_tutar, giden_banka, gelen_banka, min_olasilik):
    gecmisi_kaydet()
    adet = 0
    hedef = round(float(hedef_tutar), 2)

    adaylar = []
    for aday in st.session_state.tum_eslesmeler:
        g = aday["giden_index"]
        c = aday["silinecek_index"]
        if not aday_islenebilir_mi(g, c):
            continue
        if round(float(aday.get("Tutar", 0)), 2) != hedef:
            continue
        if aday.get("Giden_Banka", "") != giden_banka or aday.get("Gelen_Banka", "") != gelen_banka:
            continue
        if aday.get("Olasılık", 0) < min_olasilik:
            continue
        adaylar.append(aday)

    adaylar.sort(
        key=lambda x: x.get("Giden_Tarih_Obj") if pd.notna(x.get("Giden_Tarih_Obj")) else pd.Timestamp.max
    )
    kullanilan_giden = set()
    kullanilan_gelen = set()

    for aday in adaylar:
        g = aday["giden_index"]
        c = aday["silinecek_index"]
        if g in kullanilan_giden or c in kullanilan_gelen:
            continue
        onayli_cifti_isaretle(g, c)
        kullanilan_giden.add(g)
        kullanilan_gelen.add(c)
        adet += 1

    return adet


def aksiyon_al(aksiyon_tipi, giden_idx, gelen_idx, kaydet_gecmis=True):
    if kaydet_gecmis:
        gecmisi_kaydet()
    if aksiyon_tipi == "ONAYLA":
        onayli_cifti_isaretle(giden_idx, gelen_idx)
    elif aksiyon_tipi == "YANLIS_ESLESME":
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx))
    elif aksiyon_tipi == "GIDEN_DEGIL":
        st.session_state.islenen_gidenler.add(giden_idx)
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx))
    elif aksiyon_tipi == "GELEN_DEGIL":
        st.session_state.islenen_gelenler.add(gelen_idx)
        st.session_state.reddedilen_ciftler.add((giden_idx, gelen_idx))
    elif aksiyon_tipi == "IKISI_DE_DEGIL":
        st.session_state.islenen_gidenler.add(giden_idx)
        st.session_state.islenen_gelenler.add(gelen_idx)


def geri_al():
    if st.session_state.islem_gecmisi:
        son_durum = st.session_state.islem_gecmisi.pop()
        st.session_state.islenen_gidenler = set(son_durum["gidenler"])
        st.session_state.islenen_gelenler = set(son_durum["gelenler"])
        st.session_state.reddedilen_ciftler = set(son_durum["reddedilen"])
        st.session_state.onaylanan_silinecekler = list(son_durum["silinenler"])
