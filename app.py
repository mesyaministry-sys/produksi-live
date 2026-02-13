import streamlit as st
import pandas as pd
import numpy as np
import time

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🔒 LOGIN
# ==========================================
try:
    USER_RAHASIA = st.secrets["credentials"]["username"]
    PASS_RAHASIA = st.secrets["credentials"]["password"]
except:
    USER_RAHASIA = "mahesya13"
    PASS_RAHASIA = "swasa226"

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 SYSTEM LOCKED")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if u == USER_RAHASIA and p == PASS_RAHASIA:
                st.session_state["logged_in"] = True
                st.rerun()
            else: st.error("Salah")
    st.stop()

# ==========================================
# 📂 DATA SOURCE (1 FILE MASTER)
# ==========================================
# Masukkan ID File JANUARI (File Master) di sini
# Pastikan Bapak sudah menggabungkan data Feb ke file ini dan RENAME sheetnya
SHEET_ID_MASTER = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"  

# ==========================================
# 🎛️ SIDEBAR MENU
# ==========================================
with st.sidebar:
    st.header("🗂️ PILIH PERIODE")
    
    # 1. Pilih Bulan
    bulan_opsi = {"JANUARI": "Jan", "FEBRUARI": "Feb", "MARET": "Mar", "APRIL": "Apr"}
    pilih_bulan = st.selectbox("Bulan:", list(bulan_opsi.keys()))
    suffix_bulan = bulan_opsi[pilih_bulan] # Contoh: "Feb"
    
    # 2. Pilih Tanggal
    pilih_tgl = st.selectbox("Tanggal:", [str(i) for i in range(1, 32)], index=3)
    
    # 3. Konstruksi Nama Sheet (Otomatis)
    # Target Nama Sheet: "4 Feb", "14 Jan"
    target_sheet_name = f"{pilih_tgl} {suffix_bulan}"
    
    st.divider()
    st.info(f"📂 Mencari Sheet: **{target_sheet_name}**")
    
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 HEADER & LOGIC
# ==========================================
st.title(f"Laporan: {target_sheet_name} 2026")

# LOAD DATA
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_MASTER}/gviz/tq?tqx=out:csv&sheet={target_sheet_name}'

try:
    # Coba baca data
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)
    
    # =========================================================
    # 🕵️‍♂️ VALIDASI: APAKAH SHEET BENAR-BENAR ADA?
    # =========================================================
    # Google kadang mengembalikan sheet pertama (default) jika sheet yg diminta gak ada.
    # Kita cek: Apakah di Header Excel ada tulisan Tanggal/Bulan yg sesuai?
    
    is_valid = False
    
    # Ambil 10 baris pertama header jadi satu string besar
    header_text = " ".join(df_raw.iloc[:10].astype(str).values.flatten()).upper()
    
    # Cek 1: Apakah ada nama bulan yg diminta (misal "FEB") di header?
    if suffix_bulan.upper() in header_text:
        is_valid = True
    else:
        # Cek 2 (Cadangan): Jika user memberi nama sheet angka saja "4", 
        # kita cek apakah angka "4" ada di header tanggal.
        if f" {pilih_tgl} " in f" {header_text} " or f"-{pilih_tgl}-" in header_text:
             # Tapi ini agak riskan, sebaiknya patokan nama bulan.
             # Kita perketat: Kalau bulan SALAH (misal minta FEB dikasih JAN), tolak.
             if "JAN" in header_text and suffix_bulan.upper() == "FEB":
                 is_valid = False
             else:
                 is_valid = True

    # =========================================================

    if is_valid:
        # --- PROSES DATA ---
        idx_900 = -1
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            df = df_raw.iloc[idx_900:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Mapping Kolom (Sesuaikan jika ada geser kolom)
            # Asumsi: Kolom 9=Ton A, Kolom 14=Ton B
            ton_a = df.iloc[:, 9].apply(clean).sum()
            ton_b = df.iloc[:, 14].apply(clean).sum()
            total = ton_a + ton_b
            
            # TAMPILKAN
            c1, c2, c3 = st.columns(3)
            c1.metric("Line A", f"{ton_a:,.0f} T")
            c2.metric("Line B", f"{ton_b:,.0f} T")
            c3.metric("Total", f"{total:,.0f} T")
            
            st.dataframe(df.iloc[:, :15].head(10))
            
        else:
            st.warning(f"⚠️ Sheet '{target_sheet_name}' ditemukan, tapi data jam 9:00 belum diisi.")
    
    else:
        # TAMPILAN JIKA SHEET TIDAK ADA (ATAU SALAH KIRIM)
        st.error(f"⛔ Data Kosong / Sheet '{target_sheet_name}' Belum Dibuat.")
        st.caption("Pastikan nama Sheet di Excel sudah diganti jadi format 'Tanggal Bulan' (Contoh: 4 Feb).")

except Exception as e:
    st.info(f"⚠️ Belum ada data untuk **{target_sheet_name}**.")
    # Error biasanya muncul karena sheet tidak ditemukan sama sekali oleh Google
