import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ID FILE (JANGAN DIGANTI)
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY" # File Master Lama
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c" # File Baru

# ==========================================
# 🛡️ STYLE
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .success-box { padding:15px; background:#e8f5e9; border-left:5px solid #2e7d32; color:#1b5e20; }
    .warning-box { padding:15px; background:#fff3e0; border-left:5px solid #ff9800; color:#e65100; }
    .error-box { padding:15px; background:#ffebee; border-left:5px solid #c62828; color:#b71c1c; }
    </style>
""", unsafe_allow_html=True)

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
    
    # Pilih Bulan
    bulan = st.selectbox("Pilih Bulan:", ["Januari", "Februari"])
    
    # Tentukan ID File berdasarkan bulan
    if bulan == "Januari":
        ACTIVE_ID = ID_JAN
        bln_singkat = "Jan"
    else:
        ACTIVE_ID = ID_FEB
        bln_singkat = "Feb"
        
    st.divider()
    
    # Pilih Tanggal (1-31)
    tgl_angka = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=0)
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🧠 LOGIC: AUTO-SEARCH SHEET NAME
# ==========================================
st.title(f"Laporan: {tgl_angka} {bulan} 2026")

# Kita siapkan daftar nama sheet yang MUNGKIN ada di Excel Bapak
# Script akan mencoba satu per satu sampai ketemu.
kemungkinan_nama_sheet = [
    f"{tgl_angka} {bln_singkat}",  # Contoh: "1 Jan" (Format Bapak skrg)
    f"{tgl_angka}",                 # Contoh: "1" (Format Februari lama)
    f"{tgl_angka}-{bln_singkat}",   # Contoh: "1-Jan"
    f"Tgl {tgl_angka}",             # Contoh: "Tgl 1"
    f"{tgl_angka} {bulan}",         # Contoh: "1 Januari"
]

found_df = None
used_sheet_name = ""

# Mulai Mencari...
for nama_sheet in kemungkinan_nama_sheet:
    url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={nama_sheet}'
    try:
        # Coba baca
        df_temp = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)
        
        # VALIDASI PENTING:
        # Google suka kasih sheet default (Sheet 1) kalau nama sheet gak ketemu.
        # Kita cek Header-nya. Apakah ada angka tanggal yg kita minta?
        
        header_text = " ".join(df_temp.iloc[:15].astype(str).values.flatten()).upper()
        
        # Cek apakah angka tanggal (misal '14') ada di header?
        # Pakai regex biar '4' gak cocok sama '14'
        if re.search(rf"\b0?{tgl_angka}[\s\-\/]", header_text):
            # Cek juga bulannya biar gak nyasar (Jan ke Feb)
            if bln_singkat.upper() in header_text:
                found_df = df_temp
                used_sheet_name = nama_sheet
                break # KETEMU! Berhenti mencari.
        
    except:
        continue # Gak ketemu, lanjut ke kemungkinan nama berikutnya

# ==========================================
# 📊 TAMPILKAN HASIL
# ==========================================

if found_df is not None:
    # --- SHEET DITEMUKAN & VALID ---
    
    # Cari Jam 9:00
    idx_start = -1
    col_jam = found_df.iloc[:30, 0].astype(str)
    matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
    
    if not matches.empty:
        idx_start = matches.index[0]
        df_clean = found_df.iloc[idx_start:].copy()
        
        # Fungsi Bersih Angka
        def clean(x):
            try: return float(str(x).replace(',', '.').strip())
            except: return 0.0

        # Mapping Data (Januari & Februari Formatnya Sama)
        # Kolom 9 = Tonnage A, Kolom 14 = Tonnage B
        ton_a = df_clean.iloc[:, 9].apply(clean).sum()
        ton_b = df_clean.iloc[:, 14].apply(clean).sum()
        total = ton_a + ton_b
        
        rm_avg = df_clean.iloc[:, 1].apply(clean).mean()
        rot_avg = df_clean.iloc[:, 2].apply(clean).mean()
        
        # Info Sukses
        st.markdown(f'<div class="success-box">✅ DATA DITEMUKAN (Sheet: "{used_sheet_name}")</div>', unsafe_allow_html=True)
        st.write("")

        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("RM Moist", f"{rm_avg:.2f}%")
        c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
        c3.metric("Total Output", f"{total:,.0f} TON")
        
        st.divider()
        
        # Detail Line
        ca, cb = st.columns(2)
        with ca:
            st.info("Line A")
            st.metric("Prod A", f"{ton_a:,.0f} T")
            st.metric("Moist A", f"{df_clean.iloc[:, 7].apply(clean).mean():.2f}%")
        with cb:
            st.error("Line B")
            st.metric("Prod B", f"{ton_b:,.0f} T")
            st.metric("Moist B", f"{df_clean.iloc[:, 12].apply(clean).mean():.2f}%")

        # Tabel
        st.dataframe(df_clean.iloc[:, :15].head(15), use_container_width=True)
        
    else:
        st.markdown(f'<div class="warning-box">⚠️ Sheet "{used_sheet_name}" ketemu, tapi Jam 9:00 belum diisi.</div>', unsafe_allow_html=True)

else:
    # --- SHEET TIDAK DITEMUKAN ---
    st.markdown(f"""
    <div class="error-box">
        📂 DATA TIDAK TERSEDIA
    </div>
    <div style="text-align:center; margin-top:10px; color:#666;">
        <p>Aplikasi sudah mencari sheet dengan nama: <b>{tgl_angka}, {tgl_angka} {bln_singkat}, {tgl_angka}-{bln_singkat}</b>...</p>
        <p>Tapi tidak ada yang cocok/valid di Excel.</p>
        <p><i>(Kemungkinan Sheet Tanggal {tgl_angka} memang belum dibuat di file {bulan}).</i></p>
    </div>
    """, unsafe_allow_html=True)
