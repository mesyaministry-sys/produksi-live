import streamlit as st
import pandas as pd
import numpy as np
import re
import time 

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🛡️ STYLE
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .status-ok { background-color: #e8f5e9; color: #2e7d32; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;}
    .status-err { background-color: #ffebee; color: #c62828; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;}
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
# 📂 DATA SOURCE
# ==========================================
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Februari 2026": ID_FEB,
    "Januari 2026": ID_JAN,
}

# SIDEBAR
with st.sidebar:
    st.header("🎛️ MENU")
    pilihan_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    # Pilih Tanggal (1-31)
    # Default index 3 (Tanggal 4)
    pilihan_sheet = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) 
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# HEADER
st.title(f"Laporan: {pilihan_sheet} {pilihan_bulan}")

# LOAD DATA
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # 1. BACA DATA
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # =========================================================================
    # 🧠 LOGIKA HIBRIDA (BEDA BULAN, BEDA ATURAN)
    # =========================================================================
    
    is_allowed = True # Default Boleh Tampil
    pesan_blokir = ""
    
    # ATURAN 1: JIKA FEBRUARI -> WAJIB CEK HEADER (SATPAM GALAK)
    if "Februari" in pilihan_bulan:
        header_text = " ".join(df_raw.iloc[:15].astype(str).values.flatten()).upper()
        target_angka = str(pilihan_sheet)
        
        # Cari angka tanggal yang diminta di header
        # Regex: \b5\b (cari angka 5 yang berdiri sendiri)
        if not re.search(rf"\b0?{target_angka}[\s\-\/]", header_text):
            is_allowed = False
            pesan_blokir = f"⛔ DATA TIDAK DITEMUKAN (Sheet Tanggal {target_angka} Belum Ada)"

    # ATURAN 2: JIKA JANUARI -> LOLOSKAN SAJA (JANGAN DIHALANGI)
    # Karena Januari sudah lengkap, kita percaya saja pada data yang ada.
    elif "Januari" in pilihan_bulan:
        is_allowed = True

    # =========================================================================
    
    if is_allowed:
        # --- PROSES DATA (JANUARI & FEBRUARI YG VALID) ---
        
        # Cari Jangkar Jam 9:00
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            df_clean = df_raw.iloc[idx_900:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Mapping Kolom
            ton_a = df_clean.iloc[:, 9].apply(clean).sum()
            ton_b = df_clean.iloc[:, 14].apply(clean).sum()
            total = ton_a + ton_b
            
            rm_avg = df_clean.iloc[:, 1].apply(clean).mean()
            rot_avg = df_clean.iloc[:, 2].apply(clean).mean()

            # TAMPILAN DASHBOARD
            # Info Status
            if "Februari" in pilihan_bulan:
                st.markdown(f'<div class="status-ok">✅ DATA VALID (Terkonfirmasi)</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("RM Moist", f"{rm_avg:.2f}%")
            c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
            c3.metric("Total Output", f"{total:,.0f} TON")
            
            st.divider()
            
            # Line A & B
            ca, cb = st.columns(2)
            with ca:
                st.info("Line A")
                st.metric("Prod A", f"{ton_a:,.0f} T")
                st.metric("Moist A", f"{df_clean.iloc[:, 7].apply(clean).mean():.2f}%")
            with cb:
                st.error("Line B")
                st.metric("Prod B", f"{ton_b:,.0f} T")
                st.metric("Moist B", f"{df_clean.iloc[:, 12].apply(clean).mean():.2f}%")

            st.dataframe(df_clean.iloc[:, :15].head(10), use_container_width=True)
            
        else:
            # Jika Januari kosong (misal tanggal libur), tampilkan warning biasa
            st.warning("⚠️ Sheet ada, tapi belum ada data produksi (Jam 9:00 tidak ditemukan).")

    else:
        # --- JIKA DIBLOKIR (KHUSUS FEBRUARI YG BELUM ADA SHEETNYA) ---
        st.markdown(f"""
        <div class="status-err">
            {pesan_blokir}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="text-align:center; color:#666; margin-top:10px;">
            <p>Anda membuka <b>Februari Tanggal {pilihan_sheet}</b>.</p>
            <p>Sheet ini belum dibuat di Excel, sehingga Google mengirim sheet default.</p>
            <p>Sistem memblokir tampilan agar Anda tidak melihat data yang salah.</p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")
