import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI DATABASE BULANAN
# ==========================================
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "12ZVOHJf4pFImwP6W1iLZgBe56RvN1Q3a3BnKWcJeOys",             
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                   
}

st.set_page_config(page_title="Monitoring Produksi", layout="wide")
st.title("🏭 Monitoring Produksi Live")
st.caption("Created & Developer : Mahesya | 2026") 

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
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
if "MASUKKAN_ID" in SHEET_ID_AKTIF or SHEET_ID_AKTIF == "":
    st.info(f"📁 Laporan untuk bulan **{pilihan_bulan}** belum dihubungkan.")
    st.stop()

url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ==========================================
    # B. CARI JANGKAR (JAM 9:00)
    # ==========================================
    idx_900 = 6 
    found_anchor = False

    # Scan Kolom A untuk cari "9:00"
    scan_col = df_raw.iloc[:30, 0].astype(str)
    matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
    
    if not matches.empty:
        idx_900 = matches[0]
        found_anchor = True
    else:
        st.error("❌ Error: Tidak menemukan Jam 9:00 di Kolom A.")
        st.stop()

    # ==========================================
    # C. CARI PRODUK (SCANNER NAIK KE ATAS)
    # ==========================================
    produk_a = "-"
    produk_b = "-"

    def valid_prod(val):
        t = str(val).strip()
        if len(t) < 2: return False
        # Tolak Angka & Range
        if t.replace('.','').replace(',','').isdigit(): return False 
        if re.match(r'^\d+-\d+$', t): return False
        # Tolak Header
        if any(x in t.lower() for x in ["moisture", "particle", "mesh", "max", "min", "tonnage", "time"]): return False
        return True

    # --- CARI PRODUK A (KOLOM J / Index 9) ---
    # Kita cek: Baris 9:00, Baris Atasnya (8:00), Baris Atasnya Lagi (Produk)
    # Range check: idx_900 (baris 9) sampai idx_900 - 3 (naik 3 baris)
    for r in range(idx_900, max(0, idx_900-4), -1):
        # Cek area kolom 8, 9, 10
        for c in [8, 9, 10]:
            val = df_raw.iloc[r, c]
            if valid_prod(val):
                # Prioritas: Ada Angka (Z 125)
                if any(char.isdigit() for char in str(val)):
                    produk_a = str(val).strip()
                    break
        if produk_a != "-": break

    # --- CARI PRODUK B (KOLOM O / Index 14) ---
    for r in range(idx_900, max(0, idx_900-4), -1):
        # Cek area kolom 13, 14, 15
        for c in [13, 14, 15]:
            val = df_raw.iloc[r, c]
            if valid_prod(val):
                # Prioritas: Huruf Besar (HOLD)
                if str(val).isupper():
                    produk_b = str(val).strip()
                    break
        if produk_b != "-": break

    if produk_a == "-": produk_a = "(Belum Diisi)"
    if produk_b == "-": produk_b = "(Kosong)"

    # ==========================================
    # D. CARI FORMULA (SCANNER BAWAH)
    # ==========================================
    f_bbku = "-"
    f_bakar = "-"
    f_loading = "-"
    
    # Scan Baris 25 s/d 50
    for i in range(25, min(60, len(df_raw))):
        # Gabung baris jadi kalimat
        row_txt = " ".join(df_raw.iloc[i].astype(str).values).upper()
        row_txt = row_txt.replace("_", " ").replace("  ", " ")
        
        # Logika Pengambilan Data setelah ":"
        if "BBKU" in row_txt and ":" in row_txt:
            raw = row_txt.split(":")[-1].strip()
            # Bersihkan jika ada kata "FORMULA" nyangkut
            f_bbku = raw.split("FORMULA")[0].strip()
            
        if "BAHAN BAKAR" in row_txt and ":" in row_txt:
            raw = row_txt.split(":")[-1].strip()
            f_bakar = raw.split("LOADING")[0].strip()
            
        if "LOADING" in row_txt and ":" in row_txt:
            f_loading = row_txt.split(":")[-1].strip()

    # Bersihkan sisa
    for x in [f_bbku, f_bakar, f_loading]:
        x = x.replace("NAN", "").replace(",", "").strip()
    
    if len(f_bbku) < 2: f_bbku = "-"
    if len(f_bakar) < 2: f_bakar = "-"
    if len(f_loading) < 2: f_loading = "-"

    # ==========================================
    # E. DATA ANGKA
    # ==========================================
    # Ambil data mulai dari baris pertama (biasanya jam 8:00 atau 9:00)
    # Kita cari baris paling atas yang ada angka jam-nya
    idx_data_start = idx_900
    
    # Cek mundur, apakah jam 8:00 ada?
    if "8" in str(df_raw.iloc[idx_900-1, 0]):
        idx_data_start = idx_900 - 1
        
    df = df_raw.iloc[idx_data_start:].copy()
    
    df_clean = pd.DataFrame()
    
    # MAPPING KOLOM (Sesuai Gambar 28.jpg)
    df_clean["Jam Rotary A"]      = df.iloc[:, 0]
    df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
    df_clean["Rotary Moist A"]    = df.iloc[:, 2]
    
    df_clean["Jam Rotary B"]      = df.iloc[:, 3]
    df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
    df_clean["Rotary Moist B"]    = df.iloc[:, 5]
    
    df_clean["Finish Moist A"]    = df.iloc[:, 7]
    df_clean["Finish Particle A"] = df.iloc[:, 8]
    df_clean["Tonnage A"]         = df.iloc[:, 9]
    
    df_clean["Finish Moist B"]    = df.iloc[:, 12]
    df_clean["Finish Particle B"] = df.iloc[:, 13]
    df_clean["Tonnage B"]         = df.iloc[:, 14]

    # Bersihkan Angka
    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    for c in cols_angka:
        df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    # Hitung Tonnage
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
    # F. TAMPILAN
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan: **{pilihan_bulan}** | Tanggal: **{pilihan_sheet}**")
        
        st.markdown("### 🏷️ Informasi Batch Produksi")
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

        with col_info_1:
            st.markdown(f'<div class="card bg-blue"><div class="label">JENIS PRODUK A (KIRI)</div><div class="value">{produk_a}</div></div>', unsafe_allow_html=True)
        with col_info_2:
            st.markdown(f'<div class="card bg-red"><div class="label">JENIS PRODUK B (KANAN)</div><div class="value">{produk_b}</div></div>', unsafe_allow_html=True)
        
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

        st.divider()
        with st.expander("🔍 Lihat Tabel Data Mentah"):
            st.dataframe(df_clean, use_container_width=True)
    else:
        st.warning("Data kosong.")

except Exception as e:
    st.error(f"Error: {str(e)}")


