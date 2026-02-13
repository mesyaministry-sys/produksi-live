import streamlit as st
import pandas as pd
import numpy as np
import re
import time 
from PIL import Image 
from datetime import datetime

# ==========================================
# ⚙️ KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ==========================================
# 🛡️ STEALTH MODE
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    .status-box-red {
        padding: 20px; background-color: #ffebee; border: 2px solid #ff5252;
        border-radius: 10px; text-align: center; color: #b71c1c; font-weight: bold;
    }
    .status-box-green {
        padding: 10px; background-color: #e8f5e9; border: 1px solid #4caf50;
        border-radius: 5px; text-align: center; color: #2e7d32; font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 SISTEM KEAMANAN
# ==========================================
try:
    USER_RAHASIA = st.secrets["credentials"]["username"]
    PASS_RAHASIA = st.secrets["credentials"]["password"]
except:
    USER_RAHASIA = ""
    PASS_RAHASIA = ""

def check_login():
    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        st.markdown("""<style>.login-container {margin-top: 100px; padding: 40px; border-radius: 10px; background-color: #f8f9fa; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; max-width: 400px; margin-left: auto; margin-right: auto;} .stTextInput > label {font-weight:bold; color:#2c3e50;}</style>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("### 🔒 RESTRICTED ACCESS")
            st.caption("Monitoring Produksi BE")
            user_input = st.text_input("Username", key="user_input")
            pass_input = st.text_input("Password", type="password", key="pass_input")
            if st.button("LOGIN", type="primary", use_container_width=True):
                if user_input == USER_RAHASIA and pass_input == PASS_RAHASIA:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("❌ Akses Ditolak!")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    else: return True

if not check_login(): st.stop()

# ==========================================
# 🚀 APLIKASI UTAMA
# ==========================================

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
    st.caption("Created & Dev : Mahesya | 2026 🚦") 

# SIDEBAR
daftar_tanggal = [str(i) for i in range(1, 32)]
with st.sidebar:
    st.header("🗂️ Menu Utama")
    pilihan_bulan = st.selectbox("Pilih Bulan Laporan:", list(DAFTAR_FILE.keys()))
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    st.divider()
    st.subheader("📅 Periode Harian")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    # Checkbox Diagnosa (Supaya Bapak tau kenapa datanya kosong)
    debug_mode = st.checkbox("🔍 Cek Status Excel", value=True)
    
    auto_refresh = st.checkbox("🔄 Auto Refresh (60s)", value=False)
    if st.button("🔄 Refresh Manual"): st.cache_data.clear(); st.rerun()
    st.divider()
    if st.button("🔒 LOGOUT"): st.session_state["logged_in"] = False; st.rerun()
    if auto_refresh: time.sleep(60); st.cache_data.clear(); st.rerun()

# LOAD DATA
if "MASUKKAN_ID" in SHEET_ID_AKTIF or SHEET_ID_AKTIF == "":
    st.info(f"📁 Laporan untuk bulan **{pilihan_bulan}** belum dihubungkan.")
    st.stop()

url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # 1. BACA MENTAH
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # =========================================================================
    # 🕵️‍♂️ SATPAM GALAK (VALIDASI TANGGAL HEADER)
    # =========================================================================
    data_diizinkan = False
    pesan_status = ""
    
    # Bulan Target (Apa yang dipilih user di menu)
    target_bulan_nama = pilihan_bulan.split(" ")[0].upper() # "FEBRUARI"
    
    # Mapping Bulan -> Angka
    map_bulan = {"JANUARI": 1, "FEBRUARI": 2, "MARET": 3, "APRIL": 4, "MEI": 5, "JUNI": 6, 
                 "JULI": 7, "AGUSTUS": 8, "SEPTEMBER": 9, "OKTOBER": 10, "NOVEMBER": 11, "DESEMBER": 12}
    target_bulan_angka = map_bulan.get(target_bulan_nama, 0)

    # Scan 20 Baris Pertama untuk mencari Tanggal
    found_date_in_excel = None
    
    # Ambil area header (20 baris x 10 kolom pertama)
    sample_area = df_raw.iloc[:20, :10].values.flatten()
    
    for cell in sample_area:
        txt = str(cell).upper().strip()
        # Coba deteksi format tanggal (Misal: "5-JAN", "05/01/2026", "JANUARI")
        try:
            # Deteksi teks nama bulan
            bulan_terdeteksi = 0
            if "JAN" in txt and "FEB" not in txt: bulan_terdeteksi = 1
            elif "FEB" in txt: bulan_terdeteksi = 2
            elif "MAR" in txt: bulan_terdeteksi = 3
            # ... bisa dilanjutkan
            
            if bulan_terdeteksi > 0:
                found_date_in_excel = bulan_terdeteksi
                break # Ketemu tanggal, berhenti scan
        except: pass

    # KEPUTUSAN HAKIM:
    if found_date_in_excel == target_bulan_angka:
        data_diizinkan = True
        pesan_status = f"✅ Valid! Excel: Bulan {found_date_in_excel} | Menu: Bulan {target_bulan_angka}"
    elif found_date_in_excel is not None:
        data_diizinkan = False
        nama_bulan_salah = [k for k,v in map_bulan.items() if v == found_date_in_excel][0]
        pesan_status = f"⛔ DIBLOKIR: Excel masih berisi bulan **{nama_bulan_salah}** (Data Lama)."
    else:
        # Jika tidak ketemu tanggal sama sekali, kita cek apakah ada data "9:00"
        # Kalau ada data tapi tidak ada tanggal, kita anggap HANTU (Blokir) agar aman.
        data_diizinkan = False 
        pesan_status = "⚠️ Tanggal di Header Excel tidak terbaca/salah format. Mohon tulis 'Tanggal: 5 Februari' di Excel."

    # TAMPILKAN STATUS DEBUG
    if debug_mode:
        if data_diizinkan:
            st.markdown(f'<div class="status-box-green">{pesan_status}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-box-red">{pesan_status}<br>Silakan Update Tanggal di Header Excel.</div>', unsafe_allow_html=True)

    # =========================================================================

    if data_diizinkan:
        # --- PROSES DATA (SAMA SEPERTI SEBELUMNYA) ---
        idx_900 = 6 
        found_anchor = False
        scan_col = df_raw.iloc[:30, 0].astype(str)
        matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
        if not matches.empty:
            idx_900 = matches[0]
            found_anchor = True
        else:
            df_clean = pd.DataFrame()

        if found_anchor:
            produk_a, produk_b = "-", "-"
            def valid_prod(val):
                t = str(val).strip()
                if len(t) < 2 or t.replace('.','').isdigit(): return False
                if any(x in t.lower() for x in ["moist", "part", "mesh", "ton"]): return False
                return True

            for r in range(idx_900, max(0, idx_900-4), -1):
                for c in [8, 9, 10]:
                    val = df_raw.iloc[r, c]
                    if valid_prod(val) and any(char.isdigit() for char in str(val)): produk_a = str(val).strip(); break
                if produk_a != "-": break

            for r in range(idx_900, max(0, idx_900-4), -1):
                for c in [13, 14, 15]:
                    val = df_raw.iloc[r, c]
                    if valid_prod(val) and str(val).isupper(): produk_b = str(val).strip(); break
                if produk_b != "-": break

            if produk_a == "-": produk_a = "(Belum Diisi)"
            if produk_b == "-": produk_b = "(Kosong)"

            f_bbku, f_bakar, f_loading = "-", "-", "-"
            for i in range(25, min(60, len(df_raw))):
                row_txt = " ".join(df_raw.iloc[i].astype(str).values).upper()
                if "BBKU" in row_txt and ":" in row_txt: f_bbku = row_txt.split(":")[-1].split("FORMULA")[0].strip()
                if "BAHAN BAKAR" in row_txt and ":" in row_txt: f_bakar = row_txt.split(":")[-1].split("LOADING")[0].strip()
                if "LOADING" in row_txt and ":" in row_txt: f_loading = row_txt.split(":")[-1].strip()

            idx_data_start = idx_900
            if "8" in str(df_raw.iloc[idx_900-1, 0]): idx_data_start = idx_900 - 1
            
            df = df_raw.iloc[idx_data_start:].copy()
            df_clean = pd.DataFrame()
            
            df_clean["Jam"]               = df.iloc[:, 0] 
            df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
            df_clean["Rotary Moist A"]    = df.iloc[:, 2]
            df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
            df_clean["Rotary Moist B"]    = df.iloc[:, 5]
            df_clean["Finish Moist A"]    = df.iloc[:, 7]
            df_clean["Finish Particle A"] = df.iloc[:, 8]
            df_clean["Tonnage A"]         = df.iloc[:, 9]
            df_clean["Finish Moist B"]    = df.iloc[:, 12]
            df_clean["Finish Particle B"] = df.iloc[:, 13]
            df_clean["Tonnage B"]         = df.iloc[:, 14]

            cols = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                    "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
            for c in cols:
                df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
                df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

            def get_ton(series):
                total = 0
                try:
                    valid = series[~series.astype(str).isin(["-", "nan"])].dropna()
                    valid = valid[~valid.astype(str).str.contains(r'[A-Za-z]', regex=True)]
                    if not valid.empty:
                        last = str(valid.iloc[-1])
                        if "-" in last: total = float(last.split("-")[-1].strip())
                        elif last.replace('.','').isdigit(): total = float(last)
                except: total = 0
                return total

            ton_a = get_ton(df_clean["Tonnage A"])
            ton_b = get_ton(df_clean["Tonnage B"]) 
            total_gabungan = ton_a + ton_b

            # --- VISUALISASI ---
            col_info_1, col_info_2 = st.columns(2)
            st.markdown("""<style>.card { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); } .bg-blue { background: linear-gradient(135deg, #3498db, #2980b9); } .bg-red { background: linear-gradient(135deg, #e74c3c, #c0392b); } .bg-dark { background-color: #2c3e50; border: 1px solid #34495e; padding: 15px; border-radius: 8px; } .label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; margin-bottom: 5px; color: #ecf0f1; } .value { font-size: 24px; font-weight: 800; } .value-small { font-size: 18px; font-weight: bold; color: #f1c40f; }</style>""", unsafe_allow_html=True)

            with col_info_1: st.markdown(f'<div class="card bg-blue"><div class="label">JENIS PRODUK A (KIRI)</div><div class="value">{produk_a}</div></div>', unsafe_allow_html=True)
            with col_info_2: st.markdown(f'<div class="card bg-red"><div class="label">JENIS PRODUK B (KANAN)</div><div class="value">{produk_b}</div></div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">FORMULA BBKU</div><div class="value-small">{f_bbku}</div></div>', unsafe_allow_html=True)
            with c2: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">BAHAN BAKAR</div><div class="value-small">{f_bakar}</div></div>', unsafe_allow_html=True)
            with c3: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">LOADING</div><div class="value-small">{f_loading}</div></div>', unsafe_allow_html=True)

            st.divider()
            def fmt(val): return f"{val:.2f}" if pd.notnull(val) else "-"
            
            rm_a = df_clean[df_clean["RM Rotary Moist A"] > 0]["RM Rotary Moist A"]
            rot_a = df_clean[df_clean["Rotary Moist A"] > 0]["Rotary Moist A"]
            m1, m2, m3 = st.columns(3)
            m1.metric("RM Rotary Moist (Avg)", f"{fmt(rm_a.mean())}%", "40 Max")
            m2.metric("Rotary Moist (Avg)", f"{fmt(rot_a.mean())}%", "12-15")
            m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
            st.markdown("---")

            ca, cb = st.columns(2)
            with ca:
                st.markdown(f"#### 🅰️ LINE A")
                c1, c2 = st.columns(2)
                c1.metric("Moisture A", f"{fmt(df_clean['Finish Moist A'].mean())}%")
                c2.metric("Particle A", f"{fmt(df_clean['Finish Particle A'].mean())}")
                st.metric("Produksi Line A", f"{ton_a:.0f} TON")
            with cb:
                st.markdown(f"#### 🅱️ LINE B")
                c3, c4 = st.columns(2)
                c3.metric("Moisture B", f"{fmt(df_clean['Finish Moist B'].mean())}%")
                c4.metric("Particle B", f"{fmt(df_clean['Finish Particle B'].mean())}")
                st.metric("Produksi Line B", f"{ton_b:.0f} TON")

            st.markdown("---")
            st.subheader("📈 Grafik Tren Harian")
            chart_data = df_clean.dropna(subset=["Jam"]).copy()
            st.caption("1. Tren RM Rotary Moist (Input)")
            st.line_chart(chart_data, x="Jam", y=["RM Rotary Moist A", "RM Rotary Moist B"], color=["#3498db", "#e74c3c"])
            st.caption("3. Tren Finish Product Moist (Output)")
            st.line_chart(chart_data, x="Jam", y=["Finish Moist A", "Finish Moist B"], color=["#2ecc71", "#f1c40f"])
            
            st.divider()
            csv = df_clean.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Data Harian (CSV)", csv, f'laporan_{pilihan_bulan}_{pilihan_sheet}.csv', 'text/csv')

            st.subheader("🔍 Quality Control Data Check (🚦)")
            def qc(row):
                s = [''] * len(row)
                for c in ["Rotary Moist A", "Rotary Moist B"]:
                    if c in df_clean.columns and pd.notnull(row[c]):
                        try:
                            v = float(row[c])
                            i = df_clean.columns.get_loc(c)
                            if v>=16: s[i]='background-color:#ff4b4b;color:white;font-weight:bold;'
                            elif v>=14: s[i]='background-color:#f1c40f;color:black;font-weight:bold;'
                            else: s[i]='background-color:#2ecc71;color:black;font-weight:bold;'
                        except: pass
                return s
            st.dataframe(df_clean.style.apply(qc, axis=1), use_container_width=True)

    else:
        # TAMPILAN JIKA DIBLOKIR
        st.warning("⚠️ Menunggu Validasi Tanggal di Excel...")

except Exception as e:
    st.error(f"Error: {str(e)}")
