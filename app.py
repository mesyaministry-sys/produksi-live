import streamlit as st
import pandas as pd
import re

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ID FILE (PASTIKAN TIDAK TERTUKAR)
ID_JAN = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY" 
ID_FEB = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

DAFTAR_FILE = {
    "Februari 2026": ID_FEB,
    "Januari 2026": ID_JAN,
}

# ==========================================
# 🛡️ STYLE UI
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .status-ok { background-color: #e8f5e9; color: #2e7d32; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;}
    .status-empty { background-color: #f5f5f5; color: #757575; padding: 30px; border-radius: 10px; text-align: center; border: 2px dashed #bdbdbd;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 LOGIN
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
    st.header("🎛️ MENU")
    
    pilih_bulan = st.selectbox("Pilih Bulan:", list(DAFTAR_FILE.keys()), index=0)
    ACTIVE_ID = DAFTAR_FILE[pilih_bulan]
    
    # Pilih Tanggal (Format Angka 1-31)
    # Default ke 4 (biar langsung kelihatan data kalau ada)
    pilih_tgl = st.selectbox("Pilih Tanggal:", [str(i) for i in range(1, 32)], index=3) 
    
    st.divider()
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

# ==========================================
# 🚀 LOGIC UTAMA
# ==========================================
st.title(f"Laporan: Tanggal {pilih_tgl} {pilih_bulan}")

# Nama sheet sesuai info Bapak (hanya angka)
target_sheet = pilih_tgl 

try:
    url = f'https://docs.google.com/spreadsheets/d/{ACTIVE_ID}/gviz/tq?tqx=out:csv&sheet={target_sheet}'
    
    # BACA DATA
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False, on_bad_lines='skip')

    # =========================================================
    # 🕵️‍♂️ VALIDASI PINTAR (ANTI-TIPU)
    # =========================================================
    is_valid = False
    
    # Ambil 15 Baris Pertama (Header)
    header_rows = df_raw.iloc[:15]
    
    # Kita cari kombinasi kata: "DATE" atau "TANGGAL" berdekatan dengan ANGKA TANGGAL
    # Regex ini mencari: Kata (Date/Tgl/Tanggal) ... diikuti ... Angka Tanggal (misal 14)
    # (?i) artinya huruf besar/kecil dianggap sama
    
    regex_pola = rf"(?i)(DATE|TGL|TANGGAL)[\s\S]{{0,30}}\b0?{pilih_tgl}\b"
    
    # Scan baris per baris biar lebih teliti
    for idx, row in header_rows.iterrows():
        row_text = " ".join(row.astype(str).values).upper()
        
        # 1. Cek apakah ada pola "Date ... 14"
        if re.search(regex_pola, row_text):
            is_valid = True
            break
            
        # 2. Cek apakah ada pola "14-FEB" atau "14 FEB" (Khusus angka + nama bulan)
        bulan_singkat = pilih_bulan[:3].upper() # JAN / FEB
        regex_bulan = rf"\b0?{pilih_tgl}[\s\-]({bulan_singkat})"
        if re.search(regex_bulan, row_text):
            is_valid = True
            break

    # =========================================================

    if is_valid:
        # --- JIKA LOLOS VALIDASI (SHEET BENAR) ---
        
        # Cari Jam 9:00
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_start = matches.index[0]
            df = df_raw.iloc[idx_start:].copy()
            
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Cek apakah kolom cukup
            if df.shape[1] > 14:
                ton_a = df.iloc[:, 9].apply(clean).sum()
                ton_b = df.iloc[:, 14].apply(clean).sum()
                total = ton_a + ton_b
                
                rm_avg = df.iloc[:, 1].apply(clean).mean()
                rot_avg = df.iloc[:, 2].apply(clean).mean()

                # TAMPILAN
                st.markdown(f'<div class="status-ok">✅ DATA DITEMUKAN</div>', unsafe_allow_html=True)
                st.write("")

                c1, c2, c3 = st.columns(3)
                c1.metric("RM Moist", f"{rm_avg:.2f}%")
                c2.metric("Rotary Moist", f"{rot_avg:.2f}%")
                c3.metric("Total Output", f"{total:,.0f} TON")
                
                st.divider()
                st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)
            else:
                st.error("⚠️ Struktur Kolom Excel Tidak Sesuai (Kurang kolom).")
        else:
            st.info(f"⚠️ Sheet '{target_sheet}' Valid, tapi Jam 9:00 belum diisi.")
            
    else:
        # --- JIKA TIDAK LOLOS (DATA HANTU / SHEET BELUM ADA) ---
        st.markdown(f"""
        <div class="status-empty">
            <h3>📂 DATA BELUM TERSEDIA</h3>
            <p>Sheet untuk tanggal <b>{pilih_tgl}</b> belum dibuat di Excel.</p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    # Error Handler (Misal sheet beneran gak ada sama sekali di Google)
    st.markdown(f"""
    <div class="status-empty">
        <h3>📂 DATA TIDAK DITEMUKAN</h3>
        <p>Belum ada data untuk tanggal <b>{pilih_tgl}</b>.</p>
    </div>
    """, unsafe_allow_html=True)
