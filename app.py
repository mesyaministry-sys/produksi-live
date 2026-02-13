import streamlit as st
import pandas as pd
import numpy as np
import re
import time 
from PIL import Image 
from datetime import datetime

# ==========================================
# ⚙️ KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🛡️ STEALTH MODE & STYLING
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    .status-ok {
        padding: 15px; background-color: #e8f5e9; border: 1px solid #4caf50;
        border-radius: 8px; color: #2e7d32; font-weight: bold; text-align: center;
    }
    .status-error {
        padding: 15px; background-color: #ffebee; border: 1px solid #ff5252;
        border-radius: 8px; color: #c62828; font-weight: bold; text-align: center;
    }
    .empty-state {
        text-align: center; padding: 40px; background-color: #f8f9fa; 
        border: 2px dashed #d1d8e0; border-radius: 15px; color: #7f8c8d;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SISTEM KEAMANAN (LOGIN)
# ==========================================
try:
    USER_RAHASIA = st.secrets["credentials"]["username"]
    PASS_RAHASIA = st.secrets["credentials"]["password"]
except:
    USER_RAHASIA = "mahesya13"
    PASS_RAHASIA = "swasa226"

def check_login():
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        st.markdown("""<style>.login-container {margin-top: 100px; padding: 40px; border-radius: 10px; background-color: #f8f9fa; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; max-width: 400px; margin-left: auto; margin-right: auto;} .stTextInput > label {font-weight:bold; color:#2c3e50;}</style>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("### 🔒 RESTRICTED ACCESS")
            st.caption("Monitoring Produksi BE")
            user_input = st.text_input("Username", key="user_input")
            pass_input = st.text_input("Password", type="password", key="pass_input")
            if st.button("LOGIN", type="primary", use_container_width=True):
                if user_input == USER_RAHASIA and pass_input == PASS_RAHASIA:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("❌ Akses Ditolak!")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    else: return True

if not check_login(): st.stop()

# ==========================================
# 🚀 APLIKASI UTAMA
# ==========================================

# 👇 UPDATE PENTING: ID FILE FEBRUARI SUDAH SAYA GANTI DENGAN YANG BARU
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c", # <--- ID BARU (LINK BAPAK)
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                    
}

# HEADER
c_logo, c_judul = st.columns([1, 5]) 
with c_logo:
    try: st.image("logo_swasa.png.png", width=160) 
    except: st.caption("")
with c_judul:
    st.title("Monitoring Produksi BE")
    st.caption("Created & Dev : Mahesya | 2026 🚦") 

# SIDEBAR
daftar_tanggal = [str(i) for i in range(1, 32)]
with st.sidebar:
    st.header("🗂️ Menu Utama")
    pilihan_bulan = st.selectbox("Pilih Bulan Laporan:", list(DAFTAR_FILE.keys()), index=1) # Default ke Februari
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    st.divider()
    st.subheader("📅 Periode Harian")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=0) 
    
    auto_refresh = st.checkbox("🔄 Auto Refresh (60s)", value=False)
    if st.button("🔄 Refresh Manual"): st.cache_data.clear(); st.rerun()
    st.divider()
    if st.button("🔒 LOGOUT"): st.session_state["logged_in"] = False; st.rerun()
    if auto_refresh: time.sleep(60); st.cache_data.clear(); st.rerun()

# LOAD DATA
if "MASUKKAN_ID" in SHEET_ID_AKTIF or SHEET_ID_AKTIF == "":
    st.info(f"📁 Laporan untuk bulan **{pilihan_bulan}** belum dihubungkan.")
    st.stop()

url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # 1. BACA DATA DARI GOOGLE SHEET
    #    Jika sheet tidak ada (misal tgl 14 belum dibuat), Google kadang mengembalikan sheet pertama (tgl 1).
    #    Inilah penyebab error sebelumnya.
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # =========================================================================
    # 🕵️‍♂️ VALIDATOR TANGGAL PINTAR (SMART DATE CHECK)
    # =========================================================================
    # Tujuannya: Memastikan data yang tampil BENAR-BENAR tanggal yang dipilih.
    # Jika User pilih tgl 14, tapi isi Excel tgl 1 -> BLOKIR.
    
    data_valid = False
    pesan_validasi = ""
    
    # Ambil 20 baris pertama untuk mencari Header Tanggal
    header_area = df_raw.iloc[:20, :10].values.flatten()
    
    # Kita cari angka tanggal yang dipilih user (Misal "14") di header
    # Format di Excel Bapak biasanya: "Date : 4-Feb" atau "4-Feb"
    
    target_tgl = str(pilihan_sheet) # "14"
    target_bln = pilihan_bulan.split(" ")[0][:3].upper() # "FEB"
    
    found_correct_date = False
    found_any_date = False
    
    for cell in header_area:
        txt = str(cell).upper().strip()
        # Cek apakah cell ini berisi tanggal? (Misal ada kata JAN, FEB, MAR)
        if any(x in txt for x in ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]):
            found_any_date = True
            # Cek apakah tanggalnya COCOK?
            # Regex mencari pola angka tanggal. Contoh: "4-Feb" -> match "4"
            match = re.search(r'(\d+)', txt)
            if match:
                tgl_excel = match.group(1)
                # Jika angka tanggal (misal 4) sama dengan pilihan user (4) DAN Bulannya sama (FEB)
                if tgl_excel == target_tgl and target_bln in txt:
                    found_correct_date = True
                    break
    
    # KEPUTUSAN FINAL:
    if found_correct_date:
        data_valid = True
    elif not found_any_date:
        # Jika tidak ketemu tanggal sama sekali di header, tapi ada data 9:00
        # Kemungkinan format header beda, kita loloskan tapi dengan warning kecil (atau blokir biar aman)
        # Di sini kita blokir saja biar aman kalau sheetnya kosong/tidak ada.
        data_valid = False
        pesan_validasi = "Sheet Kosong / Tidak Ditemukan."
    else:
        # Ada tanggal, TAPI SALAH (Misal pilih 14, yang muncul data tgl 1)
        data_valid = False
        pesan_validasi = f"⚠️ Sheet tanggal {pilihan_sheet} belum dibuat. (Google mengembalikan data default)"

    # =========================================================================

    if data_valid:
        # --- PROSES DATA SEPERTI BIASA ---
        idx_900 = 6 
        found_anchor = False
        scan_col = df_raw.iloc[:30, 0].astype(str)
        matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
        if not matches.empty:
            idx_900 = matches[0]
            found_anchor = True
        else:
            df_clean = pd.DataFrame()

        if found_anchor:
            # Produk
            produk_a, produk_b = "-", "-"
            def valid_prod(val):
                t = str(val).strip()
                if len(t) < 2 or t.replace('.','').isdigit(): return False
                if any(x in t.lower() for x in ["moist", "part", "mesh", "ton"]): return False
                return True

            for r in range(idx_900, max(0, idx_900-4), -1):
                for c in [8, 9, 10]:
                    val = df_raw.iloc[r, c]
                    if valid_prod(val) and any(char.isdigit() for char in str(val)): produk
