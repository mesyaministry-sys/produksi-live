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
    .block-msg {
        padding: 30px; background-color: #ffebee; border: 3px solid #e53935;
        border-radius: 10px; text-align: center; color: #b71c1c;
    }
    .raw-header {
        font-family: monospace; font-size: 11px; background-color: #eee;
        padding: 10px; border-radius: 5px; margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
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
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("### 🔒 RESTRICTED ACCESS")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("LOGIN"):
                if u == USER_RAHASIA and p == PASS_RAHASIA:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("Access Denied")
        return False
    return True

if not check_login(): st.stop()

# ==========================================
# 📂 DATA SOURCE (ID BARU)
# ==========================================
# Saya sudah update ID FEBRUARI sesuai link terakhir Bapak (1YQY...)
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c", 
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                    
}

# HEADER
c_logo, c_judul = st.columns([1, 5]) 
with c_logo:
    try: st.image("logo_swasa.png.png", width=160) 
    except: st.caption("")
with c_judul:
    st.title("Monitoring Produksi BE")
    st.caption("Ver 3.0 | Strict Validator Mode") 

# SIDEBAR
daftar_tanggal = [str(i) for i in range(1, 32)]
with st.sidebar:
    st.header("🎛️ Dashboard Control")
    pilihan_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=1) # Default Feb
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    pilihan_sheet = st.selectbox("Pilih Tanggal:", daftar_tanggal, index=4) # Default tgl 5
    
    # DEBUGGER: Nyalakan ini kalau mau lihat bukti kenapa data muncul/hilang
    show_debug = st.checkbox("🕵️‍♂️ Tampilkan Inspeksi Header", value=True)
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("🔒 LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# LOAD DATA
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # 1. Tarik Data Mentah
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # =========================================================================
    # 🕵️‍♂️ INSPEKTUR HEADER (Validasi Angka Tanggal)
    # =========================================================================
    # Masalah: Pilih Tgl 5 -> Google kirim Tgl 1.
    # Solusi: Cari angka "5" di header. Kalau gak ada -> TOLAK.
    
    is_data_cocok = False
    
    # Ambil teks Header (10 baris pertama)
    header_text_raw = " ".join(df_raw.iloc[:10].astype(str).values.flatten()).upper()
    
    # CARI ANGKA TARGET (Misal "5")
    # Regex ini mencari angka yang berdiri sendiri atau diikuti tanda -/. (Misal "5-Feb", "Date: 5")
    # Tujuannya supaya tidak tertukar dengan "2025" atau "15"
    target_regex = rf"\b0?{pilihan_sheet}[\s\-\/\.]" 
    
    # Tambahan: Cek juga nama bulan biar makin akurat
    bulan_singkat = pilihan_bulan[:3].upper() # JAN, FEB, MAR
    
    # LOGIKA PENCOCOKAN:
    # 1. Harus ada angka tanggal (misal "5")
    # 2. ATAU Harus ada bulan yang benar (misal "FEB")
    #    (Kalau sheet default/nyasar biasanya isinya "1-JAN" atau "1-FEB" padahal minta "5")
    
    has_date_number = re.search(target_regex, header_text_raw)
    has_month_name = bulan_singkat in header_text_raw
    
    # Keputusan Akhir:
    # Kita anggap valid HANYA JIKA angka tanggalnya ditemukan.
    if has_date_number:
        is_data_cocok = True
    else:
        is_data_cocok = False

    # =========================================================================

    # TAMPILAN DEBUG (Biar Bapak tau apa yang terjadi)
    if show_debug:
        with st.expander("🔍 Laporan Inspeksi (Kenapa data tampil/hilang?)", expanded=True):
            c_dbg1, c_dbg2 = st.columns([3, 1])
            with c_dbg1:
                st.caption(f"Script mencari tanda: Angka **'{pilihan_sheet}'** di Header Excel.")
                st.text_area("Header yang dibaca dari Google:", header_text_raw[:300], height=80, disabled=True)
            with c_dbg2:
                if is_data_cocok:
                    st.success(f"✅ COCOK!\nAngka {pilihan_sheet} ditemukan.")
                else:
                    st.error(f"⛔ TIDAK COCOK!\nAngka {pilihan_sheet} TIDAK ADA.")

    # =========================================================================

    if is_data_cocok:
        # --- PROSES DATA (HANYA JIKA LOLOS VALIDASI) ---
        idx_900 = -1
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            df_clean = df_raw.iloc[idx_900:].copy()
            
            # Helper Bersih Angka
            def clean_num(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Hitung Total
            ton_a = df_clean.iloc[:, 9].apply(clean_num).sum()
            ton_b = df_clean.iloc[:, 14].apply(clean_num).sum()
            total_ton = ton_a + ton_b
            
            rm_a_avg = df_clean.iloc[:, 1].apply(clean_num).mean()
            rot_a_avg = df_clean.iloc[:, 2].apply(clean_num).mean()
            
            # TAMPILAN UTAMA
            c1, c2, c3 = st.columns(3)
            c1.metric("RM Rotary Moist (Avg)", f"{rm_a_avg:.2f}%")
            c2.metric("Rotary Moist (Avg)", f"{rot_a_avg:.2f}%")
            c3.metric("Total Output", f"{total_ton:,.0f} TON")
            
            st.divider()
            st.subheader("Data Detail")
            st.dataframe(df_clean.head(10), use_container_width=True)

        else:
            # Lolos validasi tanggal, tapi format jam 9:00 gak ketemu
            st.warning("⚠️ Tanggal cocok, tapi format tabel (Jam 9:00) tidak ditemukan.")

    else:
        # --- JIKA DIBLOKIR ---
        st.markdown(f"""
        <div class="block-msg">
            <h2>⛔ AKSES DITOLAK: DATA TIDAK SESUAI</h2>
            <p>Anda meminta Tanggal <b>{pilihan_sheet}</b>.</p>
            <p>Namun, data yang dikirim Google Sheet <b>tidak memiliki angka '{pilihan_sheet}'</b> di judulnya.</p>
            <hr>
            <p style="font-size:12px; color:black;">
            <b>Penyebab:</b> Sheet tanggal {pilihan_sheet} belum dibuat di Excel, sehingga Google mengirim sheet Default (Tanggal 1).<br>
            <b>Solusi:</b> Buat sheet baru di Excel, beri nama "{pilihan_sheet}", dan pastikan di Header tertulis tanggalnya.
            </p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"System Error: {e}")
