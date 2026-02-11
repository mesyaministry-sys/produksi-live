import streamlit as st
import pandas as pd
import numpy as np
import re
import time 
from PIL import Image # Library untuk gambar

# ==========================================
# ⚙️ KONFIGURASI DATABASE BULANAN
# ==========================================
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "12ZVOHJf4pFImwP6W1iLZgBe56RvN1Q3a3BnKWcJeOys",             
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                   
}

st.set_page_config(page_title="Monitoring Produksi", layout="wide")

# ==========================================
# 🖼️ HEADER DENGAN LOGO
# ==========================================
# Membagi area atas jadi 2 kolom: Logo (Kecil) & Judul (Besar)
c_logo, c_judul = st.columns([1, 5]) 

with c_logo:
    # Pastikan file 'logo_swasa.png' ada di folder yang sama!
    # Jika tidak ada, script tidak akan error tapi logo tidak muncul.
    try:
        st.image("logo_swasa.png", width=120) 
    except:
        st.caption("Logo tidak ditemukan") # Placeholder jika gambar belum diupload

with c_judul:
    st.title("🏭 Monitoring Produksi BE")
    st.caption("Created & Developer : Mahesya | 2026 🚦") 

# ==========================================
# 1. MENU SAMPING
# ==========================================
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("🗂️ Menu Utama")
    pilihan_bulan = st.selectbox("Pilih Bulan Laporan:", list(DAFTAR_FILE.keys()))
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    st.subheader("📅 Periode Harian")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    auto_refresh = st.checkbox("🔄 Auto Refresh (60s)", value=False)
    
    if st.button("🔄 Refresh Manual"):
        st.cache_data.clear()
        st.rerun()

    if auto_refresh:
        time.sleep(60) 
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 2. PROSES DATA
# ==========================================
if "MASUKKAN_ID" in SHEET_ID_AKTIF or SHEET_ID_AKTIF == "":
    st.info(f"📁 Laporan untuk bulan **{pilihan_bulan}** belum dihubungkan.")
    st.stop()

url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # --- CARI JANGKAR ---
    idx_900 = 6 
    found_anchor = False
    scan_col = df_raw.iloc[:30, 0].astype(str)
    matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
    if not matches.empty:
        idx_900 = matches[0]
        found_anchor = True
    else:
        st.error("❌ Error: Tidak menemukan Jam 9:00 di Kolom A.")
        st.stop()

    # --- CARI PRODUK ---
    produk_a, produk_b = "-", "-"
    def valid_prod(val):
        t = str(val).strip()
        if len(t) < 2: return False
        if t.replace('.','').replace(',','').isdigit(): return False 
        if re.match(r'^\d+-\d+$', t): return False
        if any(x in t.lower() for x in ["moisture", "particle", "mesh", "max", "min", "tonnage", "time"]): return False
        return True

    for r in range(idx_900, max(0, idx_900-4), -1):
        for c in [8, 9, 10]:
            val = df_raw.iloc[r, c]
            if valid_prod(val):
                if any(char.isdigit() for char in str(val)): produk_a = str(val).strip(); break
        if produk_a != "-": break

    for r in range(idx_900, max(0, idx_900-4), -1):
        for c in [13, 14, 15]:
            val = df_raw.iloc[r, c]
            if valid_prod(val):
                if str(val).isupper(): produk_b = str(val).strip(); break
        if produk_b != "-": break

    if produk_a == "-": produk_a = "(Belum Diisi)"
    if produk_b == "-": produk_b = "(Kosong)"

    # --- CARI FORMULA ---
    f_bbku, f_bakar, f_loading = "-", "-", "-"
    for i in range(25, min(60, len(df_raw))):
        row_txt = " ".join(df_raw.iloc[i].astype(str).values).upper().replace("_", " ").replace("  ", " ")
        if "BBKU" in row_txt and ":" in row_txt: f_bbku = row_txt.split(":")[-1].split("FORMULA")[0].strip()
        if "BAHAN BAKAR" in row_txt and ":" in row_txt: f_bakar = row_txt.split(":")[-1].split("LOADING")[0].strip()
        if "LOADING" in row_txt and ":" in row_txt: f_loading = row_txt.split(":")[-1].strip()

    for x in [f_bbku, f_bakar, f_loading]: x = x.replace("NAN", "").replace(",", "").strip()
    if len(f_bbku)<2: f_bbku="-"; 
    if len(f_bakar)<2: f_bakar="-"; 
    if len(f_loading)<2: f_loading="-"

    # --- OLAH DATA ---
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

    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    for c in cols_angka:
        df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    def hitung_tonnage(series):
        total = 0
        try:
            valid = series[~series.astype(str).isin(["-", "", "nan", "None"])].dropna()
            valid = valid[~valid.astype(str).str.contains(r'[A-Za-z]', regex=True)]
            if not valid.empty:
                last_val = str(valid.iloc[-1])
                if "-" in last_val: 
                    parts = last_val.split("-")
                    clean_part = parts[-1].strip()
                    if clean_part.replace('.','').isdigit(): total = float(clean_part)
                elif last_val.replace('.','').isdigit(): total = float(last_val)
        except: total = 0
        return total

    total_ton_a = hitung_tonnage(df_clean["Tonnage A"])
    total_ton_b = hitung_tonnage(df_clean["Tonnage B"]) 
    total_gabungan = total_ton_a + total_ton_b

    # ==========================================
    # F. TAMPILAN DASHBOARD
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan: **{pilihan_bulan}** | Tanggal: **{pilihan_sheet}**")
        
        col_info_1, col_info_2 = st.columns(2)
        st.markdown("""
        <style>
        .card { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .bg-blue { background: linear-gradient(135deg, #3498db, #2980b9); }
        .bg-red { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .bg-dark { background-color: #2c3e50; border: 1px solid #34495e; padding: 15px; border-radius: 8px; }
        .label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; margin-bottom: 5px; color: #ecf0f1; }
        .value { font-size: 24px; font-weight: 800; }
        .value-small { font-size: 18px; font-weight: bold; color: #f1c40f; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1: st.markdown(f'<div class="card bg-blue"><div class="label">JENIS PRODUK A (KIRI)</div><div class="value">{produk_a}</div></div>', unsafe_allow_html=True)
        with col_info_2: st.markdown(f'<div class="card bg-red"><div class="label">JENIS PRODUK B (KANAN)</div><div class="value">{produk_b}</div></div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">FORMULA BBKU</div><div class="value-small">{f_bbku}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">BAHAN BAKAR</div><div class="value-small">{f_bakar}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">LOADING</div><div class="value-small">{f_loading}</div></div>', unsafe_allow_html=True)

        st.divider()
        
        rm_a = df_clean[df_clean["RM Rotary Moist A"] > 0]["RM Rotary Moist A"]
        rm_b = df_clean[df_clean["RM Rotary Moist B"] > 0]["RM Rotary Moist B"]
        avg_rm = pd.concat([rm_a, rm_b]).mean()
        rot_a = df_clean[df_clean["Rotary Moist A"] > 0]["Rotary Moist A"]
        rot_b = df_clean[df_clean["Rotary Moist B"] > 0]["Rotary Moist B"]
        avg_rot = pd.concat([rot_a, rot_b]).mean()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{avg_rm:.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{avg_rot:.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
        
        st.markdown("---")

        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"#### 🅰️ LINE A")
            c1, c2 = st.columns(2)
            c1.metric("Moisture A", f"{df_clean['Finish Moist A'].mean():.2f}%")
            c2.metric("Particle A", f"{df_clean['Finish Particle A'].mean():.2f}")
            st.metric("Produksi Line A", f"{total_ton_a:.0f} TON")

        with cb:
            st.markdown(f"#### 🅱️ LINE B")
            c3, c4 = st.columns(2)
            c3.metric("Moisture B", f"{df_clean['Finish Moist B'].mean():.2f}%")
            c4.metric("Particle B", f"{df_clean['Finish Particle B'].mean():.2f}")
            st.metric("Produksi Line B", f"{total_ton_b:.0f} TON")

        # --- GRAFIK ---
        st.markdown("---")
        st.subheader("📈 Grafik Tren Harian")
        chart_data = df_clean.dropna(subset=["Jam"]).copy()

        st.caption("1. Tren RM Rotary Moist (Input)")
        st.line_chart(chart_data, x="Jam", y=["RM Rotary Moist A", "RM Rotary Moist B"], color=["#3498db", "#e74c3c"])
        st.caption("2. Tren Rotary Moist (Process)")
        st.line_chart(chart_data, x="Jam", y=["Rotary Moist A", "Rotary Moist B"], color=["#9b59b6", "#34495e"])
        st.caption("3. Tren Finish Product Moist (Output)")
        st.line_chart(chart_data, x="Jam", y=["Finish Moist A", "Finish Moist B"], color=["#2ecc71", "#f1c40f"])
        
        st.divider()
        
        # --- DOWNLOAD & TABEL (TRAFFIC LIGHT) ---
        csv = df_clean.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data Harian (CSV)",
            data=csv,
            file_name=f'laporan_produksi_{pilihan_bulan}_{pilihan_sheet}.csv',
            mime='text/csv',
        )

        st.subheader("🔍 Quality Control Data Check (🚦)")
        st.caption("Indikator Particle: 🔴<75 | 🔵75-79.9 | 🟢80-88 | 🟡>88")
        
        def qc_highlight(row):
            styles = [''] * len(row)
            
            # 1. ROTARY MOIST (A & B)
            for col in ["Rotary Moist A", "Rotary Moist B"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        if val >= 16.0: styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;'
                        elif val >= 14.0: styles[idx] = 'background-color: #f1c40f; color: black; font-weight: bold;'
                        else: styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;'
                    except: pass

            # 2. FINISH MOIST (A & B)
            for col in ["Finish Moist A", "Finish Moist B"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        if val > 15.0: styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;'
                        else: styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;'
                    except: pass

            # 3. PARTICLE SIZE (A & B)
            for col in ["Finish Particle A", "Finish Particle B"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        if val < 75.0: styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;'
                        elif 75.0 <= val <= 79.9: styles[idx] = 'background-color: #87CEFA; color: black; font-weight: bold;'
                        elif 80.0 <= val <= 88.0: styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;'
                        else: styles[idx] = 'background-color: #f1c40f; color: black; font-weight: bold;'
                    except: pass

            return styles

        st.dataframe(df_clean.style.apply(qc_highlight, axis=1), use_container_width=True)

    else:
        st.warning("Data kosong.")

except Exception as e:
    st.error(f"Error: {str(e)}")
