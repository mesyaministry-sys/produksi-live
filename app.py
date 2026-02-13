import streamlit as st
import pandas as pd
import numpy as np
import re
import time

# ==========================================
# ⚙️ KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🛡️ STYLE & UI
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .state-box {
        padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; font-weight: bold;
    }
    .state-success { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
    .state-error { background-color: #ffebee; color: #c62828; border: 1px solid #ef5350; }
    .state-warning { background-color: #fff3e0; color: #ef6c00; border: 1px solid #ff9800; }
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
            st.warning("🔒 SYSTEM LOCKED")
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
# 📂 DATA SOURCE
# ==========================================
# ID File FEBRUARI TERBARU (Sesuai Link Bapak)
SHEET_ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Februari 2026": SHEET_ID_FEB,  # Prioritas Februari
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                    
}

# SIDEBAR
with st.sidebar:
    st.header("🎛️ Dashboard Control")
    pilihan_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    
    # Selector Tanggal (1-31)
    # Default index=3 berarti tanggal 4 (karena array mulai dari 0)
    pilihan_sheet = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) 
    
    st.divider()
    if st.button("🔄 REFRESH DATA"):
        st.cache_data.clear()
        st.rerun()
        
    if st.button("🔒 LOGOUT"):
        st.session_state["logged_in"] = False
        st.rerun()

# HEADER
st.title(f"Laporan Produksi: {pilihan_sheet} {pilihan_bulan}")

# LOAD DATA
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # 1. Tarik Data Mentah
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ====================================================================
    # 🕵️‍♂️ VALIDASI: APAKAH SHEET INI BENAR?
    # ====================================================================
    # Google suka "Nakal". Kalau kita minta Sheet "5" tapi belum ada,
    # dia kasih Sheet "1" (Default). Kita harus cek isinya.
    
    is_valid_sheet = False
    
    # Ambil teks dari 10 baris pertama (Header area)
    header_text = " ".join(df_raw.iloc[:10].astype(str).values.flatten()).upper()
    
    # KUNCI: Cari angka tanggal yang dipilih User di dalam Header.
    # Regex mencari angka "pilihan_sheet" yang berdiri sendiri (misal "5" bukan "15" atau "50")
    # Contoh: "DATE: 5-FEB" -> Cocok. 
    # Contoh: "DATE: 1-FEB" -> Tidak Cocok (Ini sheet nyasar).
    
    target_pattern = rf"\b{pilihan_sheet}\b" # Mencari angka pasti
    
    if re.search(target_pattern, header_text):
        # Jika angka tanggal ditemukan di header -> VALID
        is_valid_sheet = True
    else:
        # Jika angka tanggal TIDAK ADA di header -> INVALID (Salah kirim sheet)
        is_valid_sheet = False

    # ====================================================================

    if is_valid_sheet:
        # --- PROSES DATA (Hanya jika sheet valid) ---
        
        # Cari Jangkar Jam 9:00
        idx_900 = -1
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            
            # Potong Data
            df_clean = df_raw.iloc[idx_900:].copy()
            
            # Mapping Kolom (Sesuai Struktur Google Sheet Bapak)
            # 0=Jam, 1=RM A, 2=Rot A, 4=RM B, 5=Rot B, 7=Fin Moist A, 8=Part A, 9=Ton A, 12=Fin Moist B, 13=Part B, 14=Ton B
            
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
            
            # --- TAMPILAN UTAMA ---
            
            # Jika Total 0, Tampilkan Pesan "Belum Input"
            if total_ton == 0 and rm_a_avg == 0:
                 st.markdown(f'<div class="state-box state-warning">⚠️ DATA KOSONG<br>Sheet ditemukan, tapi operator belum mengisi data.</div>', unsafe_allow_html=True)
            else:
                # Jika Ada Data
                st.markdown(f'<div class="state-box state-success">✅ DATA VALID TERKONFIRMASI</div>', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("RM Rotary Moist (Avg)", f"{rm_a_avg:.2f}%")
                c2.metric("Rotary Moist (Avg)", f"{rot_a_avg:.2f}%")
                c3.metric("Total Output", f"{total_ton:,.0f} TON")
                
                st.divider()
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.info("🅰️ LINE A")
                    st.metric("Moisture A", f"{df_clean.iloc[:, 7].apply(clean_num).mean():.2f}%")
                    st.metric("Produksi A", f"{ton_a:,.0f} TON")
                with col_b:
                    st.error("🅱️ LINE B")
                    st.metric("Moisture B", f"{df_clean.iloc[:, 12].apply(clean_num).mean():.2f}%")
                    st.metric("Produksi B", f"{ton_b:,.0f} TON")
                
                st.divider()
                st.subheader("🔍 Data Detail")
                
                # Format Tabel untuk Display
                df_display = pd.DataFrame({
                    "Jam": df_clean.iloc[:, 0],
                    "RM A": df_clean.iloc[:, 1],
                    "Rot A": df_clean.iloc[:, 2],
                    "RM B": df_clean.iloc[:, 4],
                    "Rot B": df_clean.iloc[:, 5],
                    "Ton A": df_clean.iloc[:, 9],
                    "Ton B": df_clean.iloc[:, 14]
                })
                st.dataframe(df_display, use_container_width=True)

        else:
            st.markdown(f'<div class="state-box state-warning">⚠️ FORMAT DATA TIDAK SESUAI<br>Tidak ditemukan baris jam "9:00" di sheet ini.</div>', unsafe_allow_html=True)

    else:
        # --- JIKA SHEET TIDAK VALID (GOOGLE MENGALIHKAN KE SHEET LAIN) ---
        st.markdown(f"""
        <div class="state-box state-error">
            ⛔ SHEET BELUM DIBUAT<br>
            <span style="font-weight:normal; font-size:14px;">
            Anda meminta data tanggal <b>{pilihan_sheet}</b>.<br>
            Namun, Google Sheet mengembalikan data tanggal lain (Default Sheet).<br>
            Ini berarti Sheet tanggal {pilihan_sheet} belum ada di file Excel.
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        # Debugging (Opsional, biar Bapak percaya)
        with st.expander("Lihat Apa yang Dikirim Google (Bukti Error)"):
            st.write("Google mengirim Header ini (Perhatikan tanggalnya beda):")
            st.text(header_text[:300])

except Exception as e:
    st.error(f"Terjadi Kesalahan: {e}")
