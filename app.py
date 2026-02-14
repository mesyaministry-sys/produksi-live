import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ID FILE (PASTIKAN BENAR)
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY" 
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Februari 2026": ID_FEB,
    "Januari 2026": ID_JAN,
}

# ==========================================
# 🛡️ STYLE
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .status-ok { background-color: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
    .status-err { background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    st.warning("🔒 SYSTEM LOCKED")
    c1, c2 = st.columns([2,1])
    with c1:
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
    
    pilih_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    ACTIVE_ID = DAFTAR_FILE[pilih_bulan]
    
    # Pilih Tanggal (Format Angka 1-31)
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) # Default 4
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 LOGIC UTAMA
# ==========================================
st.title(f"Laporan: Tanggal {pilih_tgl} {pilih_bulan}")

# Nama Sheet murni Angka ("1", "2", "3") sesuai info Bapak
target_sheet = pilih_tgl 

try:
    url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={target_sheet}'
    
    # BACA DATA (Skip bad lines biar gak crash)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False, on_bad_lines='skip')

    # =========================================================
    # 🕵️‍♂️ VALIDASI KETAT (BIAR GAK KETIPU GOOGLE)
    # =========================================================
    # Masalah: Minta sheet "14", dikasih sheet "1".
    # Solusi: Cek Header Excel. Ada gak angka "14" di sana?
    
    is_valid = False
    header_text = " ".join(df_raw.iloc[:15].astype(str).values.flatten()).upper()
    
    # Regex: Cari angka tanggal yg berdiri sendiri (misal "14")
    # \b artinya batas kata. "4" tidak akan cocok dengan "14" atau "2024".
    # Kita cari angka tanggal pilihan user di header.
    if re.search(rf"\b0?{pilih_tgl}[\s\-\/]", header_text) or re.search(rf"TANGGAL\s*:\s*{pilih_tgl}\b", header_text):
        # Tambahan: Cek Bulan (Opsional, tapi bagus buat safety)
        if "JAN" in pilih_bulan.upper() and "JAN" in header_text: is_valid = True
        elif "FEB" in pilih_bulan.upper() and ("FEB" in header_text or "DATE" in header_text): is_valid = True
        else: is_valid = False # Bulan gak cocok
    else:
        is_valid = False # Angka tanggal gak ketemu di header

    # =========================================================

    if is_valid:
        # --- DATA BENAR ---
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_start = matches.index[0]
            df = df_raw.iloc[idx_start:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Cek Kelengkapan Kolom
            if df.shape[1] > 14:
                ton_a = df.iloc[:, 9].apply(clean).sum()
                ton_b = df.iloc[:, 14].apply(clean).sum()
                total = ton_a + ton_b
                
                rm_avg = df.iloc[:, 1].apply(clean).mean()
                rot_avg = df.iloc[:, 2].apply(clean).mean()

                st.markdown(f'<div class="status-ok">✅ DATA DITEMUKAN</div>', unsafe_allow_html=True)
                st.write("")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("RM Moist", f"{rm_avg:.2f}%")
                c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
                c3.metric("Total Output", f"{total:,.0f} TON")
                
                st.divider()
                st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)
            else:
                st.error("⚠️ Struktur Kolom Excel Tidak Sesuai.")
        else:
            st.warning(f"⚠️ Sheet '{target_sheet}' ada, tapi Jam 9:00 belum diisi.")
            
    else:
        # --- DATA SALAH KIRIM / BELUM ADA ---
        st.markdown(f"""
        <div class="status-err">
            📂 DATA BELUM TERSEDIA
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"Sheet untuk tanggal **{pilih_tgl}** belum dibuat/ditemukan di Excel {pilih_bulan}.")

except Exception as e:
    # Error Handler kalau sheet sama sekali gak ketemu
    st.markdown(f"""
    <div class="status-err">
        📂 DATA TIDAK DITEMUKAN
    </div>
    """, unsafe_allow_html=True)
