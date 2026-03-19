import math
import re

import numpy as np
import pandas as pd


KELIME_DESENI = re.compile(r"[A-ZĞÜŞİÖÇ0-9]{3,}")


def banka_bul(metin):
    metin = str(metin).upper()
    bulunanlar = []
    bulunan_seti = set()

    def banka_ekle(banka_adi):
        if banka_adi not in bulunan_seti:
            bulunan_seti.add(banka_adi)
            bulunanlar.append(banka_adi)

    kisa_kodlar = {
        "TEB": r"\bTEB\b",
        "QNB": r"\bQNB\b",
        "YAPI KREDİ": r"\bYKB\b",
        "ING": r"\bİ?NG\b",
        "HALKBANK": r"\bHALK\b",
        "VAKIFBANK": r"\bVAKIF\b",
    }
    for banka, desen in kisa_kodlar.items():
        if re.search(desen, metin):
            banka_ekle(banka)

    uzun_isimler = {
        "TEB": ["EKONOMİ BANK", "EKONOMI BANK", "TÜRK EKONOMİ", "TURK EKONOMI"],
        "GARANTİ": ["GARANTİ", "GARANTI"],
        "ZİRAAT": ["ZİRAAT", "ZIRAAT", "ZIRAATBANK"],
        "HALKBANK": ["HALKBANK", "HALK BANK", "T.HALK"],
        "VAKIFBANK": ["VAKIFBANK", "VAKIF BANK", "VAKIF KATILIM"],
        "AKBANK": ["AKBANK", "AK BANK"],
        "YAPI KREDİ": ["YAPI KREDİ", "YAPI KREDI", "YAPI VE KREDİ", "KOCBANK", "KOÇBANK"],
        "İŞ BANKASI": ["İŞ BANK", "IS BANK", "İŞBANK", "ISBANK", "İŞ CEP", "İS CEP", "İŞBANKASI", "ISBANKASI"],
        "QNB": ["FİNANSBANK", "FINANSBANK", "ENPARA", "FİNANS BANK", "FINANS BANK"],
        "DENİZBANK": ["DENİZBANK", "DENIZBANK", "DENİZ BANK", "DENIZ BANK"],
        "KUVEYT TÜRK": ["KUVEYT", "KUVEYTTURK"],
        "ALBARAKA": ["ALBARAKA", "AL BARAKA"],
        "ODEA": ["ODEABANK", "ODEA BANK"],
        "FİBABANKA": ["FİBABANKA", "FIBABANKA"],
        "ŞEKERBANK": ["ŞEKERBANK", "SEKERBANK"],
        "PAPARA": ["PAPARA"],
    }
    for banka_adi, kelimeler in uzun_isimler.items():
        if any(k in metin for k in kelimeler):
            banka_ekle(banka_adi)

    return bulunanlar


def _gun_skoru(gun_farki):
    return 35.0 * math.exp(-float(gun_farki) / 1.3)


def _dakika_skoru(dakika_farki):
    return 30.0 * math.exp(-float(dakika_farki) / 45.0)


def virman_puanla_ve_bul(df, sirket_kelimeleri, maks_gun):
    df = df.reset_index(drop=True)
    adaylar_df = df[df["VIRMAN_ADAYI"] == True].copy()
    if adaylar_df.empty:
        return []

    adaylar_df["MUTLAK_TUTAR_KURUS"] = (adaylar_df["TUTAR"].abs().round(2) * 100).astype("int64")
    adaylar_df["TARIH_OBJ"] = pd.to_datetime(adaylar_df["TARİH"], format="%d.%m.%Y", errors="coerce")
    adaylar_df = adaylar_df.dropna(subset=["TARIH_OBJ"]).copy()
    if adaylar_df.empty:
        return []

    adaylar_df["ACIKLAMA_UPPER"] = adaylar_df["AÇIKLAMA"].astype(str).str.upper()
    jenerikler = {
        "İLE",
        "İÇİN",
        "BANK",
        "BANKASI",
        "ŞUBESİ",
        "HAVALE",
        "GÖNDEREN",
        "ALICI",
        "İŞLEMLERİ",
        "BEDELİ",
        "ELDEN",
        "TESLİM",
        "ALDIM",
        "NOLU",
        "GİDEN",
        "GELEN",
        "ÖDEME",
        "ÖDEMESİ",
        "HESABA",
        "HESAPTAN",
        "FAST",
        "EFT",
        "SWIFT",
        "İBAN",
        "IBAN",
        "SANAYİ",
        "TİCARET",
        "KUYUMCULUK",
        "ALTIN",
        "ALIMI",
        "ALIM",
        "SATIM",
        "SATIŞ",
        "A.Ş.",
        "A.S.",
        "LTD.",
        "ŞTİ.",
        "LİMİTED",
        "ŞİRKETİ",
        "SORG",
        "NO",
        "TÜRK",
        "A.S",
        "A.Ş",
    }
    adaylar_df["KELIMELER"] = adaylar_df["ACIKLAMA_UPPER"].apply(lambda a: {w for w in KELIME_DESENI.findall(a) if w not in jenerikler})
    adaylar_df["ACIKLAMA_BANKALARI"] = adaylar_df["AÇIKLAMA"].apply(banka_bul)

    grup = adaylar_df.groupby("MUTLAK_TUTAR_KURUS")
    tum_eslesmeler = []

    dosya_bankalari = {}
    for dosya_adi in df["KAYNAK"].unique():
        bulunan_bankalar = banka_bul(dosya_adi)
        dosya_bankalari[dosya_adi] = bulunan_bankalar[0] if bulunan_bankalar else None

    kesin_virman_kelimeleri = ["VİRMAN", "VIRMAN", "KENDİ", "KENDI", "TRANSFER", "MAHSUP"] + sirket_kelimeleri

    for tutar_kurus, data in grup:
        if len(data) <= 1:
            continue
        artilar = data[data["TUTAR"] > 0]
        eksiler = data[data["TUTAR"] < 0]
        if artilar.empty or eksiler.empty:
            continue

        for i, arti in artilar.iterrows():
            kelimeler_gelen = arti["KELIMELER"]
            tarih_arti = arti["TARIH_OBJ"]
            gelen_gercek_banka = dosya_bankalari.get(arti["KAYNAK"])
            gelen_aciklama_bankalari = arti["ACIKLAMA_BANKALARI"]

            uygun_eksiler = eksiler[(eksiler["TARIH_OBJ"] >= tarih_arti - pd.Timedelta(days=maks_gun)) & (eksiler["TARIH_OBJ"] <= tarih_arti)]
            if uygun_eksiler.empty:
                continue

            for j, eksi in uygun_eksiler.iterrows():
                tarih_eksi = eksi["TARIH_OBJ"]
                gun_farki_gercek = (tarih_arti - tarih_eksi).days

                saat_bilgisi_var = bool(
                    arti.get("SAAT_BILINIYOR", False)
                    and eksi.get("SAAT_BILINIYOR", False)
                    and pd.notna(arti["TARIH_SAAT_OBJ"])
                    and pd.notna(eksi["TARIH_SAAT_OBJ"])
                )
                dakika_farki_gercek = None
                if saat_bilgisi_var:
                    zaman_farki = (arti["TARIH_SAAT_OBJ"] - eksi["TARIH_SAAT_OBJ"]).total_seconds() / 60
                    if zaman_farki < 0:
                        continue
                    dakika_farki_gercek = float(zaman_farki)

                giden_gercek_banka = dosya_bankalari.get(eksi["KAYNAK"])
                giden_aciklama_bankalari = eksi["ACIKLAMA_BANKALARI"]
                puan = 0
                nedenler = []

                gun_skor = _gun_skoru(gun_farki_gercek)
                puan += round(gun_skor)
                if gun_farki_gercek == 0:
                    nedenler.append(f"Aynı Gün ({gun_skor:.1f})")
                else:
                    nedenler.append(f"Valör {gun_farki_gercek} Gün ({gun_skor:.1f})")

                if saat_bilgisi_var and dakika_farki_gercek is not None:
                    dakika_skor = _dakika_skoru(dakika_farki_gercek)
                    puan += round(dakika_skor)
                    if dakika_farki_gercek <= 15:
                        nedenler.append(f"Saat Yakın ({int(dakika_farki_gercek)} Dk, {dakika_skor:.1f})")
                    else:
                        nedenler.append(f"Saat Farkı ({int(dakika_farki_gercek)} Dk, {dakika_skor:.1f})")

                if arti["KAYNAK"] != eksi["KAYNAK"]:
                    puan += 10
                    nedenler.append("Farklı Bankalar")

                farkli_banka_suphesi = False
                if giden_aciklama_bankalari and giden_gercek_banka and gelen_gercek_banka:
                    for b in giden_aciklama_bankalari:
                        if b != giden_gercek_banka and b != gelen_gercek_banka:
                            farkli_banka_suphesi = True
                            break

                if not farkli_banka_suphesi and gelen_aciklama_bankalari and giden_gercek_banka and gelen_gercek_banka:
                    for b in gelen_aciklama_bankalari:
                        if b != giden_gercek_banka and b != gelen_gercek_banka:
                            farkli_banka_suphesi = True
                            break

                if farkli_banka_suphesi:
                    puan -= 30
                    nedenler.append("Farklı Banka Şüphesi")

                if gelen_gercek_banka and gelen_gercek_banka in giden_aciklama_bankalari:
                    puan += 30
                    nedenler.append("Banka Teyidi")
                if giden_gercek_banka and giden_gercek_banka in gelen_aciklama_bankalari:
                    puan += 30
                    nedenler.append("Banka Teyidi")

                aciklama_birlesik = (str(arti["AÇIKLAMA"]) + " " + str(eksi["AÇIKLAMA"])).upper()
                if any(k in aciklama_birlesik for k in kesin_virman_kelimeleri):
                    puan += 40
                    nedenler.append("Firma İbaresi")

                kelimeler_giden = eksi["KELIMELER"]
                ortak_kelimeler = kelimeler_giden.intersection(kelimeler_gelen)
                if ortak_kelimeler:
                    puan += 30
                    nedenler.append("Ortak Terim")

                if puan >= 55:
                    tum_eslesmeler.append(
                        {
                            "Olasılık": min(puan, 100),
                            "Tutar": round(tutar_kurus / 100, 2),
                            "Giden_Banka": eksi["KAYNAK"].split(".")[0],
                            "Gelen_Banka": arti["KAYNAK"].split(".")[0],
                            "Giden_Aciklama": eksi["AÇIKLAMA"],
                            "Gelen_Aciklama": arti["AÇIKLAMA"],
                            "Giden_Tarih": f"{eksi['TARİH']} {eksi['SAAT'] if eksi['SAAT'] else ''}",
                            "Gelen_Tarih": f"{arti['TARİH']} {arti['SAAT'] if arti['SAAT'] else ''}",
                            "Giden_Tarih_Obj": eksi["TARIH_SAAT_OBJ"] if pd.notna(eksi.get("TARIH_SAAT_OBJ")) else tarih_eksi,
                            "Gelen_Tarih_Obj": arti["TARIH_SAAT_OBJ"] if pd.notna(arti.get("TARIH_SAAT_OBJ")) else tarih_arti,
                            "Giden_Tutar": eksi["TUTAR"],
                            "Gelen_Tutar": arti["TUTAR"],
                            "Giden_Bakiye": eksi["BAKİYE"] if pd.notna(eksi.get("BAKİYE")) else None,
                            "Gelen_Bakiye": arti["BAKİYE"] if pd.notna(arti.get("BAKİYE")) else None,
                            "Giden_Sira": eksi.get("SIRA_NO", 0),
                            "Gelen_Sira": arti.get("SIRA_NO", 0),
                            "Nedeni": " + ".join(nedenler),
                            "silinecek_index": i,
                            "giden_index": j,
                            "banka_cifti_adet": 1,
                        }
                    )

    banka_cifti_gruplari = {}
    for idx, m in enumerate(tum_eslesmeler):
        key = (m["Tutar"], m["Giden_Banka"], m["Gelen_Banka"])
        banka_cifti_gruplari.setdefault(key, []).append(idx)

    for key, match_idxs in banka_cifti_gruplari.items():
        giden_dict = {}
        gelen_dict = {}
        giden_sira = {}
        gelen_sira = {}

        for midx in match_idxs:
            m = tum_eslesmeler[midx]
            g = m["giden_index"]
            c = m["silinecek_index"]
            if g not in giden_dict:
                giden_dict[g] = m["Giden_Tarih_Obj"]
                giden_sira[g] = m.get("Giden_Sira", 0)
            if c not in gelen_dict:
                gelen_dict[c] = m["Gelen_Tarih_Obj"]
                gelen_sira[c] = m.get("Gelen_Sira", 0)

        adet = min(len(giden_dict), len(gelen_dict))
        if adet >= 2:
            giden_sorted = sorted(giden_dict.keys(), key=lambda x: (giden_sira.get(x, 0), giden_dict[x] if pd.notna(giden_dict[x]) else pd.Timestamp.max))
            gelen_sorted = sorted(gelen_dict.keys(), key=lambda x: (gelen_sira.get(x, 0), gelen_dict[x] if pd.notna(gelen_dict[x]) else pd.Timestamp.max))

            krono_ciftler = {(giden_sorted[r], gelen_sorted[r]) for r in range(adet)}
            for midx in match_idxs:
                m = tum_eslesmeler[midx]
                m["banka_cifti_adet"] = adet
                if (m["giden_index"], m["silinecek_index"]) in krono_ciftler:
                    m["Olasılık"] = min(m["Olasılık"] + 20, 100)
                    m["Nedeni"] += " + Bakiye Sırası"
                elif adet >= 3:
                    m["Olasılık"] = max(m["Olasılık"] - 15, 0)
                    m["Nedeni"] += " + Sıra Uyumsuz"
        else:
            for midx in match_idxs:
                tum_eslesmeler[midx]["banka_cifti_adet"] = adet

    tum_eslesmeler.sort(key=lambda x: x["Olasılık"], reverse=True)
    return tum_eslesmeler
