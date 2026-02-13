import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 📂 DATA SOURCE (PASTIKAN ID INI BENAR)
# ==========================================
# ID File Januari (Yg Bapak Ganti Nama Sheetnya)
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"
# ID File Februari (Yg Baru / Masih Angka)
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
    ID_AKTIF = DAFTAR_FILE[pilih_bulan]
    
    # 2. Pilih Tanggal (Angka 1-31)
    pilih_tgl_angka = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=0)
    
    # =========================================================
    # 🔧 BAGIAN PENTING: PENYESUAIAN NAMA SHEET
    # =========================================================
    # Di sini kita atur logika pembacaan nama sheet sesuai keluhan Bapak
    
    final_sheet_name = ""
    
    if "Januari" in pilih_bulan:
        # Kalo Januari, formatnya: "1 Jan", "2 Jan" (Sesuai yg Bapak ubah)
        final_sheet_name = f"{pilih_tgl_angka} Jan"
    else:
        # Kalo Februari, formatnya: "1", "2" (Masih angka biasa/belum diubah)
        # Atau kalau Bapak sudah ubah Februari jadi "1 Feb", ganti baris bawah jadi:
        # final_sheet_name = f"{pilih_tgl_angka} Feb"
        final_sheet_name = pilih_tgl_angka 

    st.info(f"📂 Membuka Sheet: **{final_sheet_name}**")
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 LOGIC UTAMA
# ==========================================
st.title(f"Laporan: {final_sheet_name} ({pilih_bulan})")

# Construct URL
url = f'https://docs.google.com/spreadsheets/d/{ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={final_sheet_name}'

try:
    # 1. BACA DATA
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # 2. CARI JAM 9:00
    idx_start = -1
    col_jam = df_raw.iloc[:30, 0].astype(str)
    matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
    
    if not matches.empty:
        idx_start = matches.index[0]
        df = df_raw.iloc[idx_start:].copy()
        
        # 3. BERSIHKAN DATA
        def bersih(x):
            try: return float(str(x).replace(',', '.').strip())
            except: return 0.0

        # Mapping Kolom (Sesuaikan dengan Excel Bapak)
        # Asumsi: Kolom 1=RM A, 2=Rot A, 9=Ton A, 14=Ton B
        ton_a = df.iloc[:, 9].apply(bersih).sum()
        ton_b = df.iloc[:, 14].apply(bersih).sum()
        total = ton_a + ton_b
        
        rm_avg = df.iloc[:, 1].apply(bersih).mean()
        rot_avg = df.iloc[:, 2].apply(bersih).mean()
        
        # 4. TAMPILKAN
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

        # Tabel Data
        st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)

    else:
        st.warning(f"⚠️ Sheet '{final_sheet_name}' ditemukan, tapi data jam 9:00 belum diisi/kosong.")

except Exception as e:
    # PESAN ERROR JELAS
    st.error(f"❌ Sheet '{final_sheet_name}' Tidak Ditemukan.")
    st.caption("Pastikan nama sheet di Excel SAMA PERSIS dengan tulisan di kotak biru menu samping.")
    # Ini menangani kasus Februari: Kalau sheet '14' belum dibuat, dia akan error disini (Bagus, jadi ketahuan).
