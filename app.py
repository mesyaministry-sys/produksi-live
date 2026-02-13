import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ KONFIGURASI DASAR
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 📂 DATA SOURCE (ID FILE SUDAH SAYA PASANG)
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
# 🔒 LOGIN SEDERHANA (HARDCODED)
# ==========================================
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
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
    st.header("🎛️ MENU UTAMA")
    
    # 1. Pilih Bulan
    pilih_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()))
    ID_AKTIF = DAFTAR_FILE[pilih_bulan]
    
    # 2. Pilih Tanggal (1-31)
    # Default saya taruh di index 0 (Tanggal 1) biar aman
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=0)
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 LOGIC UTAMA (TANPA VALIDASI RIBET)
# ==========================================
st.title(f"Laporan: {pilih_tgl} {pilih_bulan}")

# Construct URL Google Sheet
url = f'https://docs.google.com/spreadsheets/d/{ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilih_tgl}'

try:
    # 1. BACA DATA APA ADANYA
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # 2. LANGSUNG CARI JAM 9:00 (Jangkar Data)
    # Kita tidak peduli headernya apa, yang penting ada data jam 9.
    
    idx_start = -1
    col_jam = df_raw.iloc[:30, 0].astype(str) # Cek kolom pertama, 30 baris awal
    matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
    
    if not matches.empty:
        idx_start = matches.index[0]
        
        # Potong Data mulai dari Jam 9
        df = df_raw.iloc[idx_start:].copy()
        
        # 3. BERSIHKAN & OLAH DATA
        def bersih(x):
            try: return float(str(x).replace(',', '.').strip())
            except: return 0.0

        # Ambil Kolom Penting (Sesuai posisi kolom di Excel Bapak)
        # 0=Jam, 1=RM A, 2=Rot A, 9=Ton A, 14=Ton B (Estimasi dari script sebelumnya)
        
        ton_a = df.iloc[:, 9].apply(bersih).sum()
        ton_b = df.iloc[:, 14].apply(bersih).sum()
        total = ton_a + ton_b
        
        rm_avg = df.iloc[:, 1].apply(bersih).mean()
        rot_avg = df.iloc[:, 2].apply(bersih).mean()
        
        # 4. TAMPILKAN HASIL
        c1, c2, c3 = st.columns(3)
        c1.metric("RM Moist", f"{rm_avg:.2f}%")
        c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
        c3.metric("Total Output", f"{total:,.0f} TON")
        
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.info("Line A")
            st.metric("Prod A", f"{ton_a:,.0f} T")
            st.metric("Moist A", f"{df.iloc[:, 7].apply(bersih).mean():.2f}%")
        with col_b:
            st.error("Line B")
            st.metric("Prod B", f"{ton_b:,.0f} T")
            st.metric("Moist B", f"{df.iloc[:, 12].apply(bersih).mean():.2f}%")

        # Tabel Raw Data
        st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)

    else:
        # Kalau gak ketemu jam 9:00, berarti sheet kosong atau format beda
        st.warning(f"⚠️ Data Kosong untuk Tanggal {pilih_tgl}")
        st.caption("Tidak ditemukan data mulai jam 09:00 WIB.")

except Exception as e:
    st.error("Data tidak dapat dibaca.")
    st.caption(f"Error detail: {e}")
