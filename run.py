import html as html_module
import io
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from data_processing import CSV_KLASORU, banka_dosyasi_oku, veriyi_standartlastir
from matching_engine import banka_bul, virman_puanla_ve_bul
from state import init_state
from ui_components import apply_page_style, render_settings_panel
from workflow import (
    aday_islenebilir_mi,
    aksiyon_al,
    geri_al,
    otomatik_onay_kriteri,
    toplu_onayla_ayni_tutar,
    toplu_onayla_banka_cifti,
)


def inject_keyboard_shortcuts():
    components.html(
        """
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
""",
        height=0,
    )


def analyze_files(aktif_kaynak, aktif_dosyalar, csv_dosyalari):
    standart_veriler = []
    raw_files_dict = {}
    st.session_state.okuma_uyarilari = []
    st.session_state.otomatik_islenen_sayisi = 0

    with st.spinner("Dosyalar işleniyor..."):
        if aktif_kaynak == "upload":
            for dosya in aktif_dosyalar:
                df_raw = banka_dosyasi_oku(dosya)
                if df_raw is None:
                    continue
                raw_files_dict[dosya.name] = df_raw
                st_df = veriyi_standartlastir(df_raw, dosya.name)
                if not st_df.empty:
                    standart_veriler.append(st_df)
        else:
            for dosya_adi in csv_dosyalari:
                dosya_yolu = os.path.join(CSV_KLASORU, dosya_adi)
                df_raw = banka_dosyasi_oku(dosya_yolu)
                if df_raw is None:
                    continue
                raw_files_dict[dosya_adi] = df_raw
                st_df = veriyi_standartlastir(df_raw, dosya_adi)
                if not st_df.empty:
                    standart_veriler.append(st_df)

    if not standart_veriler:
        st.session_state.analiz_yapildi = False
        st.error("CSV dosyalarından analiz edilebilir veri çıkarılamadı.")
        return

    st.session_state.raw_files = raw_files_dict
    st.session_state.ham_veriler = pd.concat(standart_veriler, ignore_index=True)
    st.session_state.tum_eslesmeler = virman_puanla_ve_bul(
        st.session_state.ham_veriler,
        st.session_state.dinamik_firma_kelimeleri,
        st.session_state.maks_gun_farki,
    )

    st.session_state.islenen_gidenler = set()
    st.session_state.islenen_gelenler = set()
    st.session_state.reddedilen_ciftler = set()
    st.session_state.onaylanan_silinecekler = []
    st.session_state.islem_gecmisi = []
    st.session_state.analiz_yapildi = True


def render_import_panel():
    st.markdown("### Veri Yükle")
    yukleme_tab, klasor_tab = st.tabs(["Dosya Yükle", "Klasörden Oku"])

    with yukleme_tab:
        yuklenen_dosyalar = st.file_uploader("CSV ekstreleri yükleyin", type=["csv"], accept_multiple_files=True)
        if yuklenen_dosyalar:
            st.markdown(f"**{len(yuklenen_dosyalar)} dosya seçildi**")
            for f in yuklenen_dosyalar:
                st.caption(f"{f.name} ({f.size/1024:.1f} KB)")

    with klasor_tab:
        csv_dosyalari = []
        if os.path.isdir(CSV_KLASORU):
            csv_dosyalari = sorted([f for f in os.listdir(CSV_KLASORU) if f.lower().endswith(".csv")])

        if csv_dosyalari:
            st.markdown(f"**banka csv klasöründe {len(csv_dosyalari)} dosya bulundu**")
            for f in csv_dosyalari:
                boyut = os.path.getsize(os.path.join(CSV_KLASORU, f)) / 1024
                st.caption(f"{f} ({boyut:.1f} KB)")
        else:
            st.info("banka csv klasöründe CSV dosyası bulunamadı.")

    aktif_dosyalar = yuklenen_dosyalar if yuklenen_dosyalar else None
    aktif_kaynak = "upload" if yuklenen_dosyalar else ("folder" if csv_dosyalari else None)

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        baslat_btn = st.button("Analizi Başlat", type="primary", use_container_width=True, disabled=(aktif_kaynak is None))

    return baslat_btn, aktif_kaynak, aktif_dosyalar, csv_dosyalari


def get_kalan_adaylar():
    kalan_adaylar = []
    for aday in st.session_state.tum_eslesmeler:
        g = aday["giden_index"]
        c = aday["silinecek_index"]
        if g in st.session_state.islenen_gidenler:
            continue
        if c in st.session_state.islenen_gelenler:
            continue
        if (g, c) in st.session_state.reddedilen_ciftler:
            continue
        kalan_adaylar.append(aday)
    return kalan_adaylar


def auto_approve_if_needed(kalan_adaylar):
    if not st.session_state.otomatik_onay_aktif or not kalan_adaylar:
        return

    otomatik_adet = 0
    for aday in kalan_adaylar:
        if not otomatik_onay_kriteri(aday, st.session_state.otomatik_onay_esigi):
            continue
        g = aday["giden_index"]
        c = aday["silinecek_index"]
        if not aday_islenebilir_mi(g, c):
            continue
        aksiyon_al("ONAYLA", g, c, kaydet_gecmis=False)
        otomatik_adet += 1

    if otomatik_adet > 0:
        st.session_state.otomatik_islenen_sayisi += otomatik_adet
        st.success(f"{otomatik_adet} eşleşme otomatik onaylandı.")
        st.rerun()


def render_stats(kalan_adaylar):
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
    st.caption(f"İlerleme: {progress_yuzde}% | Bekleyen aday: {kalan_sayi}")


def render_exports():
    silinen_dict = {}
    for idx in st.session_state.onaylanan_silinecekler:
        row = st.session_state.ham_veriler.iloc[idx]
        kaynak_dosya = row["KAYNAK"]
        orijinal_satir = row["ORIJINAL_INDEX"]
        silinen_dict.setdefault(kaynak_dosya, []).append(orijinal_satir)

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        for dosya_adi, raw_df in st.session_state.raw_files.items():
            export_df = raw_df.copy().astype(str).replace(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", regex=True)
            export_df.insert(0, "DURUM", "")
            silinecek_satirlar = silinen_dict.get(dosya_adi, [])
            export_df.loc[silinecek_satirlar, "DURUM"] = "SİLİNDİ"
            export_df.columns = ["DURUM"] + [f"Sütun {i+1}" for i in range(len(raw_df.columns))]
            styled_df = export_df.style.apply(
                lambda row: ["background-color: #fef08a"] * len(row) if row.name in silinecek_satirlar else [""] * len(row),
                axis=1,
            )
            styled_df.to_excel(writer, index=False, sheet_name="".join([c for c in dosya_adi if c not in r"\/*?:[]"])[:31])

    st.download_button(
        label="Kontrol Raporunu İndir (Excel)",
        data=excel_buffer.getvalue(),
        file_name="Islem_Raporu.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )

    giden_hesap_kodu_map = {}
    if st.session_state.banka_hesap_kodlari:
        for aday in st.session_state.tum_eslesmeler:
            g_idx = aday["giden_index"]
            c_idx = aday["silinecek_index"]
            if g_idx in st.session_state.islenen_gidenler and c_idx in st.session_state.islenen_gelenler:
                gelen_kaynak = st.session_state.ham_veriler.iloc[c_idx]["KAYNAK"]
                gelen_bankalari = banka_bul(gelen_kaynak)
                gelen_banka_adi = gelen_bankalari[0] if gelen_bankalari else None
                if gelen_banka_adi and gelen_banka_adi in st.session_state.banka_hesap_kodlari:
                    giden_hesap_kodu_map[g_idx] = st.session_state.banka_hesap_kodlari[gelen_banka_adi]

    temiz_df = st.session_state.ham_veriler.drop(index=st.session_state.onaylanan_silinecekler).copy()
    for idx, hesap_kodu in giden_hesap_kodu_map.items():
        if idx in temiz_df.index:
            temiz_df.at[idx, "AÇIKLAMA"] = str(temiz_df.at[idx, "AÇIKLAMA"]) + " - " + hesap_kodu
    temiz_df = temiz_df.reset_index(drop=True)

    banka_gruplari = temiz_df.groupby("KAYNAK")
    buton_kolonlari = st.columns(3)
    sayac = 0
    for dosya_adi, data in banka_gruplari:
        luca_df = pd.DataFrame()
        luca_df["TARİH"] = data["TARİH"]
        luca_df["AÇIKLAMA"] = data["AÇIKLAMA"]
        luca_df["TUTAR"] = data["TUTAR"].apply(lambda x: f"{x:.2f}".replace(".", ","))

        csv_buffer = io.BytesIO()
        luca_df.to_csv(csv_buffer, index=False, sep=";", encoding="cp1254")
        with buton_kolonlari[sayac % 3]:
            st.download_button(
                label=f"{dosya_adi[:20]}...",
                data=csv_buffer.getvalue(),
                file_name=f"LUCA_{dosya_adi.split('.')[0]}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        sayac += 1


def render_current_candidate(kalan_adaylar):
    aday = kalan_adaylar[0]
    g_idx = aday["giden_index"]
    c_idx = aday["silinecek_index"]

    toplam_aday = len(st.session_state.tum_eslesmeler)
    tamamlanan_aday = max(0, toplam_aday - len(kalan_adaylar))
    ilerleme_orani = 0.0 if toplam_aday == 0 else min(1.0, tamamlanan_aday / toplam_aday)
    st.progress(ilerleme_orani, text=f"Bekleyen olası eşleşme sayısı: {len(kalan_adaylar)}")

    confidence_color = "#34d399" if aday["Olasılık"] >= 90 else "#fbbf24" if aday["Olasılık"] >= 75 else "#f87171"
    nedenler = [r.strip() for r in aday["Nedeni"].split("+")]
    neden_html = "".join(f"<span class='reason-chip'>{html_module.escape(n)}</span>" for n in nedenler)

    giden_aciklama_safe = html_module.escape(str(aday["Giden_Aciklama"]))
    gelen_aciklama_safe = html_module.escape(str(aday["Gelen_Aciklama"]))
    giden_banka_safe = html_module.escape(str(aday["Giden_Banka"]))
    gelen_banka_safe = html_module.escape(str(aday["Gelen_Banka"]))
    giden_tarih_safe = html_module.escape(str(aday["Giden_Tarih"]))
    gelen_tarih_safe = html_module.escape(str(aday["Gelen_Tarih"]))

    giden_bakiye = aday.get("Giden_Bakiye")
    gelen_bakiye = aday.get("Gelen_Bakiye")
    giden_bakiye_str = f"{giden_bakiye:,.2f} ₺" if giden_bakiye is not None else "—"
    gelen_bakiye_str = f"{gelen_bakiye:,.2f} ₺" if gelen_bakiye is not None else "—"

    giden_html = f"""
    <div class='txn-card' style='border-top: 3px solid #f87171;'>
        <div style='font-weight:700; color:#f87171; font-size:14px; margin-bottom:12px;'>ÇIKIŞ</div>
        <div class='txn-row'><span class='txn-lbl'>Banka</span><span class='txn-val'>{giden_banka_safe}</span></div>
        <div class='txn-row'><span class='txn-lbl'>Tarih</span><span class='txn-val'>{giden_tarih_safe}</span></div>
        <div class='txn-row'><span class='txn-lbl'>Tutar</span><span class='txn-amount' style='color:#f87171;'>{aday['Giden_Tutar']:,.2f} ₺</span></div>
        <div class='txn-row'><span class='txn-lbl'>Bakiye</span><span class='txn-val' style='color:#94a3b8;'>{giden_bakiye_str}</span></div>
        <div style='margin-top:10px; padding-top:10px; border-top:1px solid rgba(148,163,184,0.08);'>
            <span class='txn-lbl'>Açıklama</span>
            <div style='color:#cbd5e1; font-size:12px; margin-top:4px; line-height:1.5;'>{giden_aciklama_safe}</div>
        </div>
    </div>"""

    gelen_html = f"""
    <div class='txn-card' style='border-top: 3px solid #34d399;'>
        <div style='font-weight:700; color:#34d399; font-size:14px; margin-bottom:12px;'>GİRİŞ</div>
        <div class='txn-row'><span class='txn-lbl'>Banka</span><span class='txn-val'>{gelen_banka_safe}</span></div>
        <div class='txn-row'><span class='txn-lbl'>Tarih</span><span class='txn-val'>{gelen_tarih_safe}</span></div>
        <div class='txn-row'><span class='txn-lbl'>Tutar</span><span class='txn-amount' style='color:#34d399;'>+{aday['Gelen_Tutar']:,.2f} ₺</span></div>
        <div class='txn-row'><span class='txn-lbl'>Bakiye</span><span class='txn-val' style='color:#94a3b8;'>{gelen_bakiye_str}</span></div>
        <div style='margin-top:10px; padding-top:10px; border-top:1px solid rgba(148,163,184,0.08);'>
            <span class='txn-lbl'>Açıklama</span>
            <div style='color:#cbd5e1; font-size:12px; margin-top:4px; line-height:1.5;'>{gelen_aciklama_safe}</div>
        </div>
    </div>"""

    st.markdown(
        f"""
        <div class='panel'>
            <div style='display:flex; align-items:center; gap:20px; margin-bottom:20px; flex-wrap:wrap;'>
                <div style='width:80px;height:80px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,0.3);border:3px solid {confidence_color};color:{confidence_color};font-size:22px;font-weight:800;'>%{aday['Olasılık']}</div>
                <div style='flex:1;'>{neden_html}</div>
            </div>
            <div style='display:grid; grid-template-columns:1fr 1fr; gap:14px;'>
                {giden_html}
                {gelen_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    b_geri, b_atla, b_onayla, b_toplu = st.columns([1, 2, 2, 3])
    with b_geri:
        st.button("Geri Dön (W)", use_container_width=True, disabled=(len(st.session_state.islem_gecmisi) == 0), on_click=geri_al)
    with b_atla:
        st.button("Yanlış Eşleşme (A)", use_container_width=True, on_click=aksiyon_al, args=("YANLIS_ESLESME", g_idx, c_idx))
    with b_onayla:
        st.button("Onayla (D)", type="primary", use_container_width=True, on_click=aksiyon_al, args=("ONAYLA", g_idx, c_idx))
    with b_toplu:
        toplu_basildi = st.button(
            f"Aynı Tutarı Toplu Onayla (≥%{st.session_state.toplu_onay_esigi})",
            use_container_width=True,
        )
        if toplu_basildi:
            toplu_adet = toplu_onayla_ayni_tutar(aday["Tutar"], st.session_state.toplu_onay_esigi)
            st.success(f"{toplu_adet} eşleşme onaylandı.")
            st.rerun()

    banka_cifti_adet = aday.get("banka_cifti_adet", 1)
    if banka_cifti_adet >= 2:
        giden_ids = set()
        gelen_ids = set()
        for a in kalan_adaylar:
            if (
                round(float(a.get("Tutar", 0)), 2) == round(float(aday["Tutar"]), 2)
                and a.get("Giden_Banka") == aday["Giden_Banka"]
                and a.get("Gelen_Banka") == aday["Gelen_Banka"]
            ):
                giden_ids.add(a["giden_index"])
                gelen_ids.add(a["silinecek_index"])
        aktif_cift = min(len(giden_ids), len(gelen_ids))
        if aktif_cift >= 2:
            st.info(f"{aday['Giden_Banka']} → {aday['Gelen_Banka']} arasında aynı tutarda {aktif_cift} aday bulundu.")
            if st.button(
                f"{aday['Giden_Banka']} → {aday['Gelen_Banka']} Kronolojik Toplu Onay",
                use_container_width=True,
            ):
                cift_adet = toplu_onayla_banka_cifti(
                    aday["Tutar"],
                    aday["Giden_Banka"],
                    aday["Gelen_Banka"],
                    st.session_state.toplu_onay_esigi,
                )
                st.success(f"{cift_adet} eşleşme onaylandı.")
                st.rerun()

    r_col1, r_col2, r_col3 = st.columns(3)
    with r_col1:
        st.button("Çıkış Virman Değil (1)", use_container_width=True, on_click=aksiyon_al, args=("GIDEN_DEGIL", g_idx, c_idx))
    with r_col2:
        st.button("Giriş Virman Değil (2)", use_container_width=True, on_click=aksiyon_al, args=("GELEN_DEGIL", g_idx, c_idx))
    with r_col3:
        st.button("İkisi de Virman Değil (3)", use_container_width=True, on_click=aksiyon_al, args=("IKISI_DE_DEGIL", g_idx, c_idx))


def main():
    init_state()
    apply_page_style()
    inject_keyboard_shortcuts()
    render_settings_panel()

    st.markdown("---")
    baslat_btn, aktif_kaynak, aktif_dosyalar, csv_dosyalari = render_import_panel()

    if baslat_btn and aktif_kaynak:
        analyze_files(aktif_kaynak, aktif_dosyalar, csv_dosyalari)

    if st.session_state.okuma_uyarilari:
        with st.expander(f"Okuma Uyarıları ({len(st.session_state.okuma_uyarilari)})", expanded=False):
            for uyari in st.session_state.okuma_uyarilari:
                st.warning(uyari)

    if not st.session_state.analiz_yapildi:
        return

    kalan_adaylar = get_kalan_adaylar()
    auto_approve_if_needed(kalan_adaylar)
    render_stats(kalan_adaylar)

    if len(kalan_adaylar) == 0:
        st.success(f"İnceleme tamamlandı. {len(st.session_state.onaylanan_silinecekler)} kayıt işaretlendi.")
        st.markdown("### Rapor")
        render_exports()
        return

    render_current_candidate(kalan_adaylar)


if __name__ == "__main__":
    main()
