# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import re
import difflib
from datetime import datetime
import string
import io
import os

# -------------------------
# Helper dan konfigurasi
# -------------------------

STOPWORDS = {
    "bulan","ini","juga","ya","assalamualaikum","ustadz","pak","ibu","saya",
    "untuk","atas","nama","anak","santri","bayar","pembayaran","rp","ribu","rb",
    "sebesar","berapa","dengan","yg","telah","sudah","kpd","ke","di","dan",
    "jadi","pakai","uang","sako","saku", "SPO", "uang saki", "ananda",
    "januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus",
    "september", "oktober", "november", "desember"
}

def bersihkan_teks(teks):
    teks = teks.replace("\n", " ")
    teks = teks.translate(str.maketrans('', '', string.punctuation))
    teks = re.sub(r'\s+', ' ', teks).strip()
    return teks

def kata_list(teks):
    return re.findall(r"[A-Za-zÀ-ÿ]+|\d+", teks)

def deteksi_semua_kata(teks, daftar_kata):
    tokens = kata_list(teks.lower())
    hasil = []
    for i, t in enumerate(tokens):
        cocok = difflib.get_close_matches(t, daftar_kata, n=1, cutoff=0.78)
        if cocok:
            hasil.append((i, cocok[0]))
    return hasil, tokens

def extract_name_from_window(tokens, idx):
    n = len(tokens)
    TRIGGER = {"an", "an.", "a.n", "a/n", "atas", "atasnama", "atas_nama", "ananda", "untuk", "nama", "santri", "santriwati"}

    def is_name_token(tok):
        return tok.isalpha() and tok.lower() not in STOPWORDS and len(tok) > 1

    def get_name_sequence(start_idx, max_words=3):
        name_parts = []
        for i in range(start_idx, min(start_idx + max_words, n)):
            if is_name_token(tokens[i]):
                name_parts.append(tokens[i].capitalize())
            else:
                break
        return " ".join(name_parts) if name_parts else None

    name = get_name_sequence(idx + 1, max_words=2)
    if name: return name

    for j in range(max(0, idx - 5), min(n, idx + 10)):
        if tokens[j].lower() in TRIGGER:
            name = get_name_sequence(j + 1, max_words=3)
            if name: return name

    for j in range(idx + 1, min(n, idx + 6)):
        name = get_name_sequence(j, max_words=2)
        if name: return name

    return "-"

def ekstrak_nominal_dari_window(window_text):
    teks_bersih = window_text.replace(".", "").replace(",", "")
    m = re.search(r"(\d{3,}|\d+)\s*(ribu|rb|k)?", teks_bersih, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except:
            return m.group(1)
    return "-"

def analisis_pesan(teks_input, keterangan_bulan):
    teks_clean = bersihkan_teks(teks_input)
    lower_clean = teks_clean.lower()
    daftar_kata_kunci = ["spp","spb","sppu","sppp", "uang saku", "uang sako","uang spp", "saku", "sako"]
    detected, tokens = deteksi_semua_kata(lower_clean, daftar_kata_kunci)

    hasil = []
    tahun = datetime.now().year

    for idx, found in detected:
        start = max(0, idx-5)
        end = min(len(tokens), idx+7)
        window_tokens = tokens[start:end]
        window_text = " ".join(window_tokens)

        jenis = "SPP" if any(x in found for x in ["spp","spb","sppu","sppp"]) else "Uang Saku"
        nama = extract_name_from_window(tokens, idx)
        nominal = ekstrak_nominal_dari_window(window_text)
        keterangan = f"{jenis} {keterangan_bulan} - {tahun} {nama}".strip()

        hasil.append({
            "Tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Keterangan Pembayaran": keterangan,
            "Nominal": nominal,
            "Potongan Pesan": window_text
        })

    return hasil

def to_excel(df):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Riwayat Pembayaran')
    writer.close()
    return output.getvalue()

# ------------------------- Streamlit App -------------------------

st.set_page_config(page_title="AI Pondok - Deteksi Pembayaran", layout="centered")
st.title("AI Pondok – Deteksi Pembayaran Otomatis")

st.markdown("""
Aplikasi ini **mendeteksi SPP / Uang Saku, nama santri, dan nominal** dari pesan teks.
**Setiap analisis disimpan otomatis** ke riwayat.
""")

# --- Inisialisasi Riwayat di Session State ---
if 'riwayat_df' not in st.session_state:
    st.session_state.riwayat_df = pd.DataFrame(columns=[
        "Tanggal", "Keterangan Pembayaran", "Nominal", "Potongan Pesan"
    ])

# Flag for submission via Enter key
if 'submit_triggered_by_enter' not in st.session_state:
    st.session_state.submit_triggered_by_enter = False

def set_submit_flag():
    st.session_state.submit_triggered_by_enter = True

# --- Input Form ---
with st.form("form_input"):
    teks_input_value = st.text_area("Masukkan teks pesan dari orang tua:", height=120, key="teks_input_area")
    keterangan_bulan_value = st.text_input("Keterangan bulan (contoh: Januari):", key="keterangan_bulan_input", on_change=set_submit_flag)
    submit_button_clicked = st.form_submit_button("Analisis & Simpan ke Riwayat")

# Check if submit was triggered by button click OR by Enter key in 'keterangan_bulan'
if submit_button_clicked or st.session_state.submit_triggered_by_enter:
    # Reset the flag immediately after checking it, to prevent re-triggering on subsequent reruns
    if st.session_state.submit_triggered_by_enter:
        st.session_state.submit_triggered_by_enter = False

    # Retrieve current values from session state to ensure they are up-to-date
    current_teks_input = st.session_state.teks_input_area
    current_keterangan_bulan = st.session_state.keterangan_bulan_input

    if current_teks_input.strip() and current_keterangan_bulan.strip():
        hasil = analisis_pesan(current_teks_input, current_keterangan_bulan)
        if hasil:
            df_baru = pd.DataFrame(hasil)
            st.session_state.riwayat_df = pd.concat([st.session_state.riwayat_df, df_baru], ignore_index=True)
            st.success(f"{len(hasil)} pembayaran baru ditambahkan ke riwayat!")
            st.dataframe(df_baru)
        else:
            st.warning("Tidak ada pembayaran terdeteksi.")
    else:
        st.error("Isi teks dan bulan terlebih dahulu.")

# --- Tampilkan Riwayat ---
st.markdown("---")
st.subheader("Riwayat Semua Pembayaran")

if not st.session_state.riwayat_df.empty:
    # Edit per baris
    edited_df = st.data_editor(
        st.session_state.riwayat_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Keterangan Pembayaran": st.column_config.TextColumn(
                "Keterangan (bisa edit nama)",
                help="Klik sel untuk edit nama santri"
            )
        }
    )
    st.session_state.riwayat_df = edited_df

    # Download semua data
    st.download_button(
        label="Download Semua Riwayat ke Excel",
        data=to_excel(st.session_state.riwayat_df),
        file_name=f"riwayat_pembayaran_pondok_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Belum ada data. Lakukan analisis pertama.")

# --- Reset Riwayat (Opsional) ---
if st.button("Hapus Semua Riwayat"):
    st.session_state.riwayat_df = pd.DataFrame(columns=[
        "Tanggal", "Keterangan Pembayaran", "Nominal", "Potongan Pesan"
    ])
    st.success("Riwayat dihapus!")
    st.experimental_rerun()