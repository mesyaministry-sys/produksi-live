import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 📂 DATA SOURCE
# ==========================================
# ID File Januari (Master Lama)
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"
# ID File Februari (Master Baru)
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Januari 2026": ID_JAN,
    "Februari 2026": ID_FEB,
}

# ==========================================
# 🔒 LOGIN
# ==========================================
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.warning("🔒 SYSTEM LOCKED")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if u == "mahesya13" and p == "swasa226":
                st.session_state["logged_in"] = True
                st.rerun()
            else: st.error("Salah")
    st.stop()

# ==========================================
# 🎛️ SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🎛️ MENU")
    
    # 1. Pilih Bulan
    pilih_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()))
    ACTIVE_ID = DAFTAR_FILE[pilih_bulan]
    
    # Singkatan Bulan untuk pencarian
    bulan_short = "Jan" if "Januari" in pilih_bulan else "Feb"
    
    # 2. Pilih Tanggal (1-31)
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=0)
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# HEADER
st.title(f"Laporan: {pilih_tgl} {pilih_bulan}")

# ==========================================
# 🧠 LOGIC: AUTO-SEARCH (PENCARI OTOMATIS)
# ==========================================
# Script akan mencoba berbagai kemungkinan nama sheet
possible_names = [
    str(pilih_tgl),                     # Coba angka saja ("1")
    f"{pilih_tgl} {bulan_short}",       # Coba angka + bulan ("1 Jan")
    f"{pilih_tgl}-{bulan_short}",       # Coba strip ("1-Jan")
    f"0{pilih_tgl}" if len(pilih_tgl)==1 else str(pilih_tgl) # Coba pakai nol ("01")
]

found_df = None
used_name = ""

# Loop mencari sheet yang ada
for sheet_name in possible_names:
    url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    try:
        df_temp = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)
        
        # VALIDASI PENTING:
        # Cek apakah Header Excel mengandung Tanggal yang diminta?
        # Supaya tidak tertipu sheet default Google.
        header_text = " ".join(df_temp.iloc[:15].astype(str).values.flatten()).upper()
        
        # Cari angka tanggal yang berdiri sendiri
        if re.search(rf"\b0?{pilih_tgl}[\s\-\/]", header_text):
            # Cek juga bulan (biar Jan gak ketukar Feb)
            if bulan_short.upper() in header_text:
                found_df = df_temp
                used_name = sheet_name
                break # KETEMU! Stop mencari.
                
    except:
        continue # Gagal di nama ini, coba nama berikutnya

# ==========================================
# 📊 TAMPILAN
# ==========================================

if found_df is not None:
    # --- DATA DITEMUKAN ---
    
    # Cari Jam 9:00
    idx_start = -1
    col_jam = found_df.iloc[:30, 0].astype(str)
    matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
    
    if not matches.empty:
        idx_start = matches.index[0]
        df = found_df.iloc[idx_start:].copy()
        
        def clean(x):
            try: return float(str(x).replace(',', '.').strip())
            except: return 0.0

        # Mapping Kolom
        ton_a = df.iloc[:, 9].apply(clean).sum()
        ton_b = df.iloc[:, 14].apply(clean).sum()
        total = ton_a + ton_b
        
        rm_avg = df.iloc[:, 1].apply(clean).mean()
        rot_avg = df.iloc[:, 2].apply(clean).mean()
        
        st.success(f"✅ Data Ditemukan (Sheet: '{used_name}')")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("RM Moist", f"{rm_avg:.2f}%")
        c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
        c3.metric("Total Output", f"{total:,.0f} TON")
        
        st.divider()
        st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)
        
    else:
        st.warning(f"⚠️ Sheet '{used_name}' ada, tapi format data (Jam 9:00) tidak ditemukan.")

else:
    # --- DATA TIDAK DITEMUKAN ---
    st.info(f"📂 Data Tanggal {pilih_tgl} Belum Tersedia.")
    st.caption("Sistem sudah mencari sheet dengan nama '1', '1 Jan', dll tapi tidak ditemukan atau belum diisi.")
