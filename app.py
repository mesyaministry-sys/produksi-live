import streamlit as st
import pandas as pd
import re
import time 

# ==========================================
# ⚙️ KONFIGURASI & STYLE
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .status-ok { background-color: #e8f5e9; padding: 15px; border-radius: 8px; color: #2e7d32; text-align: center; font-weight: bold; }
    .status-err { background-color: #ffebee; padding: 15px; border-radius: 8px; color: #c62828; text-align: center; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
# ==========================================
# Bypass login ribet untuk testing, pakai hardcode aman
USER_RAHASIA = "mahesya13"
PASS_RAHASIA = "swasa226"

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("🔒 SILAKAN LOGIN")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("LOGIN"):
            if u == USER_RAHASIA and p == PASS_RAHASIA:
                st.session_state["logged_in"] = True
                st.rerun()
            else: st.error("Salah")
    st.stop()

# ==========================================
# 📂 DATA SOURCE (ID FILE FEBRUARI BAPAK)
# ==========================================
SHEET_ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c" # ID BARU

DAFTAR_FILE = {
    "Februari 2026": SHEET_ID_FEB,
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
}

# SIDEBAR
with st.sidebar:
    st.header("🎛️ MENU")
    pilihan_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    # Pilih Tanggal (Angka 1-31)
    # Kita set default ke 4 agar langsung muncul data yang ada
    tgl_pilihan = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) 
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# HEADER
st.title(f"Laporan Harian: {tgl_pilihan} {pilihan_bulan}")

# ==========================================
# 📥 LOAD & VALIDASI DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={tgl_pilihan}'

try:
    # 1. BACA DATA DARI GOOGLE
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # 2. VALIDASI KETAT: APAKAH INI SHEET YANG BENAR?
    # Masalah: Minta Sheet 14 -> Dikasih Sheet 4 (Default)
    # Solusi: Cek apakah angka "14" ada di Header Excel?
    
    is_valid = False
    
    # Ambil 15 baris pertama (Area Header)
    header_text = " ".join(df_raw.iloc[:15].astype(str).values.flatten()).upper()
    
    # Logika Pencocokan:
    # Cari angka tanggal pilihan user (misal '14')
    # Pastikan angka itu berdiri sendiri atau diikuti bulan (misal '14-FEB' atau 'DATE: 14')
    # Regex \b = batas kata, supaya '4' tidak cocok dengan '14' atau '2024'
    target_pattern = rf"\b0?{tgl_pilihan}[\s\-\/]" 
    
    # Cek Bulan juga (FEB)
    bulan_singkat = pilihan_bulan[:3].upper() # FEB
    
    if re.search(target_pattern, header_text) and bulan_singkat in header_text:
        is_valid = True
    else:
        # Gagal Validasi (Salah Sambung dari Google)
        is_valid = False

    # ==========================================
    # 📊 TAMPILKAN HASIL
    # ==========================================
    
    if is_valid:
        # --- JIKA DATA VALID (Sheet Ditemukan & Cocok) ---
        
        # Cari baris Jam 9:00 untuk mulai ambil data
        idx_900 = -1
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            df_clean = df_raw.iloc[idx_900:].copy()
            
            # Helper Pembersih Angka
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Hitung Total (Sesuaikan indeks kolom dengan format Bapak)
            # Kolom 9 = Tonnage A, Kolom 14 = Tonnage B (Berdasarkan script sebelumnya)
            ton_a = df_clean.iloc[:, 9].apply(clean).sum()
            ton_b = df_clean.iloc[:, 14].apply(clean).sum()
            total = ton_a + ton_b
            
            rm_avg = df_clean.iloc[:, 1].apply(clean).mean()
            rot_avg = df_clean.iloc[:, 2].apply(clean).mean()

            # TAMPILAN DASHBOARD
            st.markdown(f'<div class="status-ok">✅ DATA DITEMUKAN (Valid)</div>', unsafe_allow_html=True)
            st.write("") # Spacer
            
            c1, c2, c3 = st.columns(3)
            c1.metric("RM Rotary Moist", f"{rm_avg:.2f}%")
            c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
            c3.metric("Total Output", f"{total:,.0f} TON")
            
            st.divider()
            
            # Tampilkan Tabel
            st.subheader("📋 Tabel Detail")
            st.dataframe(df_clean.iloc[:, :15].head(15), use_container_width=True)
            
        else:
            st.warning("⚠️ Header Tanggal Cocok, tapi tidak ada data Jam 9:00.")

    else:
        # --- JIKA DATA TIDAK VALID (Sheet Belum Ada) ---
        # Ini tampilan yang Bapak inginkan untuk tanggal yang belum diinput
        st.markdown(f"""
        <div style="text-align:center; padding:40px; background-color:#f1f3f4; border-radius:10px;">
            <h3 style="color:#7f8c8d;">📂 DATA BELUM TERSEDIA</h3>
            <p>Sheet untuk tanggal <b>{tgl_pilihan} {pilihan_bulan}</b> belum dibuat di Google Sheet.</p>
            <hr>
            <p style="font-size:12px; color:#95a5a6;">
            (Sistem memblokir data karena Google mengirim sheet default yang tidak sesuai permintaan).
            </p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Terjadi Kesalahan: {e}")
