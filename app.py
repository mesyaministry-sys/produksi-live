import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI DATABASE BULANAN
# ==========================================
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "MASUKKAN_ID_SHEET_FEBRUARI_DISINI",             
    "Maret 2026": "MASUKKAN_ID_SHEET_MARET_DISINI",                   
}

st.set_page_config(page_title="Monitoring Produksi", layout="wide")
st.title("🏭 Monitoring Produksi Live")
st.caption("Created : Mahesya") 

# ==========================================
# 1. MENU SAMPING (SIDEBAR)
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
    # B. SMART SEARCH (VERSI FINAL INDEX 8 & 13)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 

    try:
        # 1. Cari Posisi Baris Jam 9:00
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0] # Ini Baris 9 (Jam 9:00)
            
            # Target Baris Produk: SATU BARIS DI ATAS Jam 9:00
            idx_produk = idx_start - 1
            
            # --- AMBIL PRODUK A (KIRI) ---
            # INSTRUKSI: KOLOM INDEX 8 (Kolom I)
            val_a = str(df_raw.iloc[idx_produk, 8]).strip()
            
            # Validasi: Tidak kosong & bukan header
            if len(val_a) > 1 and "tonnage" not in val_a.lower() and "particle" not in val_a.lower():
                produk_a = val_a

            # --- AMBIL PRODUK B (KANAN) ---
            # INSTRUKSI: KOLOM INDEX 13 (Kolom N)
            val_b = str(df_raw.iloc[idx_produk, 13]).strip()
            
            if len(val_b) > 1 and "tonnage" not in val_b.lower() and "particle" not in val_b.lower():
                produk_b = val_b
            
    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL (PERBAIKAN OUTPUT 0 TON)
    # ==========================================
    
    # Ambil data mulai dari baris Jam 9:00
    df = df_raw.iloc[idx_start:].copy() 
    
    # MAPPING KOLOM (PASTIKAN TONNAGE BENAR DI KOLOM 9 & 14)
    # Index 9 = Kolom J (Sebelah Z 125)
    # Index 14 = Kolom O (Sebelah Product Hold)
    
    df_clean = pd.DataFrame()
    max_col = df.shape[1]
    
    # Rotary A
    df_clean["Jam Rotary A"]      = df.iloc[:, 0]
    df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
    df_clean["Rotary Moist A"]    = df.iloc[:, 2]
    
    # Rotary B
    df_clean["Jam Rotary B"]      = df.iloc[:, 3]
    df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
    df_clean["Rotary Moist B"]    = df.iloc[:, 5]
    
    # Finish A (Index 7, 8, 9)
    df_clean["Finish Moist A"]    = df.iloc[:, 7] if max_col > 7 else 0 
    df_clean["Finish Particle A"] = df.iloc[:, 8] if max_col > 8 else 0 
    df_clean["Tonnage A"]         = df.iloc[:, 9] if max_col > 9 else 0  # <-- TONNAGE A (INDEX 9)
    
    # Finish B (Index 12, 13, 14)
    df_clean["Finish Moist B"]    = df.iloc[:, 12] if max_col > 12 else 0
    df_clean["Finish Particle B"] = df.iloc[:, 13] if max_col > 13 else 0 
    df_clean["Tonnage B"]         = df.iloc[:, 14] if max_col > 14 else 0 # <-- TONNAGE B (INDEX 14)

    # ==========================================
    # D. BERSIHKAN ANGKA & HITUNG TONNAGE
    # ==========================================
    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    for c in cols_angka:
        df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    # FUNGSI HITUNG TONNAGE (FIXED)
    def hitung_tonnage(series):
        total = 0
        try:
            # Ambil data yang valid
            valid = series[~series.astype(str).isin(["-", "", "nan", "None"])].dropna()
            if not valid.empty:
                last_val = str(valid.iloc[-1])
                # Jika format "1-5", ambil 5
                if "-" in last_val: 
                    parts = last_val.split("-")
                    clean_part = parts[-1].strip() # Hapus spasi
                    if clean_part.replace('.','').isdigit():
                        total = float(clean_part)
                # Jika angka biasa "5"
                elif last_val.replace('.','').isdigit(): 
                    total = float(last_val)
        except: 
            total = 0
        return total

    total_ton_a = hitung_tonnage(df_clean["Tonnage A"])
    total_ton_b = hitung_tonnage(df_clean["Tonnage B"]) 
    total_gabungan = total_ton_a + total_ton_b

    # ==========================================
    # E. TAMPILAN DASHBOARD
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan: **{pilihan_bulan}** | Tanggal: **{pilihan_sheet}**")
        
        st.markdown("### 🏷️ Informasi Batch Produksi")
        col_info_1, col_info_2 = st.columns(2)
        
        st.markdown("""
        <style>
        .box-info { padding: 15px; border-radius: 8px; color: white; text-align: center; font-weight: bold; }
        .biru { background-color: #3498db; } .merah { background-color: #e74c3c; }
        .judul { font-size: 14px; opacity: 0.9; margin-bottom: 5px; } .isi { font-size: 24px; }
        </style>
        """, unsafe_allow_html=True)

        txt_a = produk_a if produk_a not in ["-", "nan", ""] else "(Belum Diisi)"
        txt_b = produk_b if produk_b not in ["-", "nan", ""] else "(Kosong)"

        with col_info_1:
            st.markdown(f'<div class="box-info biru"><div class="judul">JENIS PRODUK A (KIRI)</div><div class="isi">{txt_a}</div></div>', unsafe_allow_html=True)
        with col_info_2:
            st.markdown(f'<div class="box-info merah"><div class="judul">JENIS PRODUK B (KANAN)</div><div class="isi">{txt_b}</div></div>', unsafe_allow_html=True)
        
        st.divider()

        # METRIK UTAMA
        st.subheader("🔥 Rotary Process (Gabungan A & B)")
        
        gab_rm = pd.concat([df_clean["RM Rotary Moist A"], df_clean["RM Rotary Moist B"]])
        gab_rot = pd.concat([df_clean["Rotary Moist A"], df_clean["Rotary Moist B"]])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{gab_rm.mean():.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{gab_rot.mean():.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
        
        st.markdown("---")

        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"#### 🅰️ LINE A")
            c1, c2 = st.columns(2)
            c1.metric("Moisture A", f"{df_clean['Finish Moist A'].mean():.2f}%")
            c2.metric("Particle Size A", f"{df_clean['Finish Particle A'].mean():.2f}")
            st.metric("Produksi Line A", f"{total_ton_a:.0f} TON")

        with cb:
            st.markdown(f"#### 🅱️ LINE B")
            c3, c4 = st.columns(2)
            c3.metric("Moisture B", f"{df_clean['Finish Moist B'].mean():.2f}%")
            c4.metric("Particle Size B", f"{df_clean['Finish Particle B'].mean():.2f}")
            st.metric("Produksi Line B", f"{total_ton_b:.0f} TON")

        st.divider()
        with st.expander("🔍 Lihat Tabel Data Mentah"):
            st.dataframe(df_clean, use_container_width=True)
    else:
        st.warning("Data kosong.")

except Exception as e:
    st.error(f"Error: {str(e)}")
