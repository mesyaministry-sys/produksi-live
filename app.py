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
    # B. SMART SEARCH (PRODUK & FORMULA)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    
    # Variabel Baru: Formula & Loading
    f_bbku = "-"
    f_bakar = "-"
    f_loading = "-"
    
    idx_start = 6 

    try:
        # 1. CARI POSISI JAM 9:00
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0] # Baris Jam 9:00
            
            # --- CARI PRODUK (DI ATAS JAM 9:00) ---
            idx_produk = idx_start - 1
            
            # Produk A (Kolom Index 9 / J)
            val_a = str(df_raw.iloc[idx_produk, 9]).strip()
            if len(val_a) > 1 and "tonnage" not in val_a.lower(): produk_a = val_a

            # Produk B (Kolom Index 14 / O)
            val_b = str(df_raw.iloc[idx_produk, 14]).strip()
            if len(val_b) > 1 and "tonnage" not in val_b.lower(): produk_b = val_b
            
            # --- CARI FORMULA & LOADING (FITUR BARU) ---
            # Kita scan Kolom A (Index 0) dari baris 25 sampai 50 (Area Bawah)
            area_bawah = df_raw.iloc[25:55, 0].astype(str).values.flatten()
            
            for cell in area_bawah:
                txt = cell.upper()
                # Cek BBKU
                if "BBKU" in txt:
                    parts = cell.split(":")
                    if len(parts) > 1: f_bbku = parts[-1].strip()
                # Cek BAHAN BAKAR
                elif "BAHAN BAKAR" in txt:
                    parts = cell.split(":")
                    if len(parts) > 1: f_bakar = parts[-1].strip()
                # Cek LOADING
                elif "LOADING" in txt:
                    parts = cell.split(":")
                    if len(parts) > 1: f_loading = parts[-1].strip()

    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL
    # ==========================================
    df = df_raw.iloc[idx_start:].copy() 
    
    # MAPPING KOLOM
    df_clean = pd.DataFrame()
    max_col = df.shape[1]
    
    df_clean["Jam Rotary A"]      = df.iloc[:, 0]
    df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
    df_clean["Rotary Moist A"]    = df.iloc[:, 2]
    df_clean["Jam Rotary B"]      = df.iloc[:, 3]
    df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
    df_clean["Rotary Moist B"]    = df.iloc[:, 5]
    
    df_clean["Finish Moist A"]    = df.iloc[:, 7] if max_col > 7 else 0 
    df_clean["Finish Particle A"] = df.iloc[:, 8] if max_col > 8 else 0 
    df_clean["Tonnage A"]         = df.iloc[:, 9] if max_col > 9 else 0  
    
    df_clean["Finish Moist B"]    = df.iloc[:, 12] if max_col > 12 else 0
    df_clean["Finish Particle B"] = df.iloc[:, 13] if max_col > 13 else 0 
    df_clean["Tonnage B"]         = df.iloc[:, 14] if max_col > 14 else 0 

    # BERSIHKAN ANGKA
    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    for c in cols_angka:
        df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    # HITUNG TONNAGE
    def hitung_tonnage(series):
        total = 0
        try:
            valid = series[~series.astype(str).isin(["-", "", "nan", "None"])].dropna()
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
    # D. TAMPILAN DASHBOARD
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan
