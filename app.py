import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🛡️ STYLE & CSS
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .status-ok { background-color: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
    .status-warning { background-color: #fff3e0; color: #ef6c00; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
    .status-empty { background-color: #f5f5f5; color: #616161; padding: 20px; border-radius: 10px; text-align: center; border: 2px dashed #bdbdbd;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📂 DATA SOURCE
# ==========================================
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Februari 2026": ID_FEB,
    "Januari 2026": ID_JAN,
}

# ==========================================
# 🔒 LOGIN SEDERHANA
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
# 🎛️ SIDEBAR CONTROL
# ==========================================
with st.sidebar:
    st.header("🎛️ MENU")
    
    # 1. Pilih Bulan
    pilih_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    ACTIVE_ID = DAFTAR_FILE[pilih_bulan]
    
    # 2. Pilih Tanggal (1-31)
    # Default index=3 (Tanggal 4) biar pas buka langsung ada isinya (buat test)
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3)
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🧠 LOGIC UTAMA (ANTI-CRASH)
# ==========================================

# 1. TENTUKAN NAMA SHEET YANG DICARI
# Ini kuncinya biar Januari dan Februari tidak bertengkar
if "Januari" in pilih_bulan:
    # Januari formatnya: "1 Jan", "2 Jan"
    target_sheet_name = f"{pilih_tgl} Jan"
else:
    # Februari formatnya: "1", "2", "3" (Masih angka biasa)
    target_sheet_name = f"{pilih_tgl}"

st.title(f"Laporan: {pilih_tgl} {pilih_bulan}")
# st.caption(f"Mencari Sheet bernama: **'{target_sheet_name}'**") # Debugging info

# 2. URL
url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={target_sheet_name}'

try:
    # 3. BACA DATA
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # 4. VALIDASI HEADER (PENCEGAH DATA HANTU/NGACO)
    # Kita pastikan sheet yang dikirim Google benar-benar sheet yang kita minta.
    # Google suka kirim Sheet 1 kalau Sheet 14 gak ada. Kita harus tolak itu.
    
    is_valid = False
    header_text = " ".join(df_raw.iloc[:15].astype(str).values.flatten()).upper()
    
    # Logic Validasi:
    # Cari angka tanggal yang diminta (misal '14') di header Excel.
    # Regex \b mencegah '4' cocok dengan '14'.
    if re.search(rf"\b0?{pilih_tgl}[\s\-\/]", header_text):
        # Cek Bulan juga biar makin aman
        bulan_singkat = pilih_bulan[:3].upper() # JAN / FEB
        if bulan_singkat in header_text:
            is_valid = True
        else:
            is_valid = False
    else:
        is_valid = False

    # ==========================================
    # 📊 TAMPILKAN HASIL
    # ==========================================
    
    if is_valid:
        # --- DATA DITEMUKAN & VALID ---
        
        # Cari Jam 9:00
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_start = matches.index[0]
            df = df_raw.iloc[idx_start:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Mapping Kolom
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
            
            ca, cb = st.columns(2)
            with ca:
                st.info("Line A")
                st.metric("Prod A", f"{ton_a:,.0f} T")
                st.metric("Moist A", f"{df.iloc[:, 7].apply(clean).mean():.2f}%")
            with cb:
                st.error("Line B")
                st.metric("Prod B", f"{ton_b:,.0f} T")
                st.metric("Moist B", f"{df.iloc[:, 12].apply(clean).mean():.2f}%")
                
            st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)
            
        else:
            st.markdown(f'<div class="status-warning">⚠️ Sheet ada, tapi data kosong (Jam 9:00 belum diisi).</div>', unsafe_allow_html=True)
            
    else:
        # --- DATA TIDAK VALID / SHEET BELUM ADA ---
        # Ini akan muncul kalau Bapak buka Feb Tgl 14 (yang belum dibuat)
        st.markdown(f"""
        <div class="status-empty">
            <h3>📂 DATA BELUM TERSEDIA</h3>
            <p>Sheet untuk tanggal <b>{pilih_tgl}</b> belum dibuat di file Excel <b>{pilih_bulan}</b>.</p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    # MENANGKAP ERROR (ANTI CRASH)
    # Kalau sheet bener-bener gak ada, biasanya masuk sini
    st.markdown(f"""
    <div class="status-empty">
        <h3>📂 DATA TIDAK DITEMUKAN</h3>
        <p>Belum ada sheet bernama <b>"{target_sheet_name}"</b> di file {pilih_bulan}.</p>
    </div>
    """, unsafe_allow_html=True)
