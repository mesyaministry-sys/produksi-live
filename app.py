import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI ANTI-CRASH
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
    .status-warn { background-color: #fff3e0; color: #e65100; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
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
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) 
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 LOGIC UTAMA (DENGAN PENANGANAN ERROR LENGKAP)
# ==========================================
st.title(f"Laporan: Tanggal {pilih_tgl} {pilih_bulan}")

# TENTUKAN NAMA SHEET YANG DICARI (HARDCODED BIAR PASTI)
if "Januari" in pilih_bulan:
    target_sheet = f"{pilih_tgl} Jan" # Format Januari: "1 Jan"
else:
    target_sheet = pilih_tgl          # Format Februari: "1"

# st.write(f"Mencari Sheet: **{target_sheet}**") # Debug

# GUNAKAN BLOK TRY-EXCEPT BESAR AGAR TIDAK MUNCUL "OH NO"
try:
    url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={target_sheet}'
    
    # BACA DATA (Tambahkan error_bad_lines=False untuk mencegah crash di baris rusak)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False, on_bad_lines='skip')

    # CEK APAKAH DATAFRAME KOSONG ATAU RUSAK
    if df_raw.empty or df_raw.shape[1] < 2:
        # Anggap sheet tidak ditemukan
        raise ValueError("Sheet Kosong")

    # =========================================================
    # 🕵️‍♂️ VALIDASI SEDERHANA (TAPI EFEKTIF)
    # =========================================================
    # Cek Header: Apakah ada angka tanggal yang diminta?
    header_text = " ".join(df_raw.iloc[:15].astype(str).values.flatten()).upper()
    
    # Cari angka tanggal yang diminta (misal 14)
    # \b artinya harus angka itu sendiri (4 tidak sama dengan 14)
    angka_ketemu = re.search(rf"\b0?{pilih_tgl}[\s\-\/]", header_text) or re.search(rf"TANGGAL\s*:\s*{pilih_tgl}\b", header_text)
    
    # Logika Penentuan Validitas
    is_valid = False
    if angka_ketemu:
        # Cek Bulan jika perlu
        if "JAN" in pilih_bulan.upper() and "JAN" in header_text: is_valid = True
        elif "FEB" in pilih_bulan.upper(): is_valid = True # Februari agak longgar karena kadang header cuma "Date: 4"
        else: is_valid = False
    
    # =========================================================

    if is_valid:
        # --- DATA VALID ---
        
        # Cari Jam 9:00
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_start = matches.index[0]
            df = df_raw.iloc[idx_start:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # CEK JUMLAH KOLOM SEBELUM AKSES (MENCEGAH CRASH)
            jml_kolom = df.shape[1]
            
            if jml_kolom > 14: # Pastikan ada sampai kolom O (indeks 14)
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
                st.markdown(f'<div class="status-warn">⚠️ Kolom Data Kurang (Mungkin format Excel berubah).</div>', unsafe_allow_html=True)
        else:
             st.markdown(f'<div class="status-warn">⚠️ Sheet "{target_sheet}" ditemukan, tapi Jam 9:00 kosong.</div>', unsafe_allow_html=True)
            
    else:
        # --- DATA TIDAK VALID (GOOGLE SALAH KIRIM) ---
        st.markdown(f"""
        <div class="status-err">
            📂 DATA BELUM TERSEDIA
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"Sheet **'{target_sheet}'** belum dibuat di Excel.")

except Exception as e:
    # --- MENANGKAP ERROR (BIAR GAK CRASH OH NO) ---
    # Jika sheet benar-benar tidak ada di Google, dia masuk sini.
    st.markdown(f"""
    <div class="status-err">
        📂 DATA BELUM ADA
    </div>
    """, unsafe_allow_html=True)
    # st.write(f"Debug Info: {e}") # Nyalakan jika ingin liat error asli
