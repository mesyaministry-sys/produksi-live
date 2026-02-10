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
    # B. PENCARIAN DATA (PRODUK & FORMULA)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    
    # Variabel Formula
    f_bbku = "-"
    f_bakar = "-"
    f_loading = "-"
    
    idx_start = 6 

    try:
        # --- 1. CARI FORMULA (SCAN SELURUH KOLOM A) ---
        # Kita cari di kolom paling kiri, baris 20 ke bawah (area footer)
        footer_area = df_raw.iloc[20:, 0].astype(str).values
        
        for cell in footer_area:
            txt = cell.upper().replace("_", " ").strip()
            
            # Ambil data setelah titik dua (:)
            if "BBKU" in txt:
                if ":" in cell: f_bbku = cell.split(":")[-1].strip()
            
            if "BAHAN BAKAR" in txt:
                if ":" in cell: f_bakar = cell.split(":")[-1].strip()
                
            if "LOADING" in txt:
                if ":" in cell: f_loading = cell.split(":")[-1].strip()

        # --- 2. CARI POSISI JAM 9:00 ---
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0] # Baris Jam 9:00 (Row 9)
            
            # --- FUNGSI VALIDASI NAMA PRODUK ---
            def is_product_name(val):
                t = str(val).strip()
                if len(t) < 2: return False
                
                # Tolak Header / Satuan
                blacklist = ["moisture", "particle", "mesh", "max", "min", "avg", "tonnage", "checker", "paraph", "time", "%"]
                if any(x in t.lower() for x in blacklist): return False
                
                # Tolak Angka Murni (misal "80,01" atau "10")
                if t.replace('.','').replace(',','').isdigit(): return False
                
                # Tolak Range (misal "1-5")
                if re.match(r'^\d+-\d+$', t): return False
                
                return True

            # --- CARI PRODUK A (KOLOM I / Index 8) ---
            # Kita ambil 3 kandidat: Baris 8, 9, 10 pada Kolom I
            # Lalu kita pilih mana yang BUKAN angka dan BUKAN header
            kandidat_a = [
                df_raw.iloc[idx_start-1, 8], # Baris 8
                df_raw.iloc[idx_start, 8],   # Baris 9
                df_raw.iloc[idx_start+1, 8]  # Baris 10
            ]
            
            for k in kandidat_a:
                if is_product_name(k):
                    produk_a = str(k).strip()
                    break # Ketemu yang valid, stop.

            # --- CARI PRODUK B (KOLOM N / Index 13) ---
            kandidat_b = [
                df_raw.iloc[idx_start-1, 13], # Baris 8
                df_raw.iloc[idx_start, 13],   # Baris 9
                df_raw.iloc[idx_start+1, 13]  # Baris 10
            ]
            
            for k in kandidat_b:
                if is_product_name(k):
                    produk_b = str(k).strip()
                    break

    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL & TONNAGE
    # ==========================================
    df = df_raw.iloc[idx_start:].copy() 
    
    # Mapping Kolom
    df_clean = pd.DataFrame()
    max_col = df.shape[1]
    
    df_clean["Jam Rotary A"]      = df.iloc[:, 0]
    df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
    df_clean["Rotary Moist A"]    = df.iloc[:, 2]
    df_clean["Jam Rotary B"]      = df.iloc[:, 3]
    df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
    df_clean["Rotary Moist B"]    = df.iloc[:, 5]
    
    # Finish A (Index 7, 8, 9)
    df_clean["Finish Moist A"]    = df.iloc[:, 7] if max_col > 7 else 0 
    df_clean["Finish Particle A"] = df.iloc[:, 8] if max_col > 8 else 0 
    df_clean["Tonnage A"]         = df.iloc[:, 9] if max_col > 9 else 0  
    
    # Finish B (Index 12, 13, 14)
    df_clean["Finish Moist B"]    = df.iloc[:, 12] if max_col > 12 else 0
    df_clean["Finish Particle B"] = df.iloc[:, 13] if max_col > 13 else 0 
    df_clean["Tonnage B"]         = df.iloc[:, 14] if max_col > 14 else 0 

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
            # Ambil hanya yang valid (angka atau range)
            valid = series[~series.astype(str).isin(["-", "", "nan", "None"])].dropna()
            
            # Buang text produk jika tidak sengaja masuk (misal Z 125 masuk kolom tonnage)
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
    # D. TAMPILAN DASHBOARD
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan: **{pilihan_bulan}** | Tanggal: **{pilihan_sheet}**")
        
        # --- INFO PRODUK ---
        st.markdown("### 🏷️ Informasi Batch Produksi")
        col_info_1, col_info_2 = st.columns(2)
        
        txt_a = produk_a if produk_a not in ["-", "nan", ""] else "(Belum Diisi)"
        txt_b = produk_b if produk_b not in ["-", "nan", ""] else "(Kosong)"

        st.markdown("""
        <style>
        .box-info { padding: 15px; border-radius: 8px; color: white; text-align: center; font-weight: bold; margin-bottom: 10px; }
        .biru { background-color: #3498db; } 
        .merah { background-color: #e74c3c; }
        .abu { background-color: #34495e; border: 1px solid #7f8c8d; }
        .judul { font-size: 14px; opacity: 0.8; margin-bottom: 5px; text-transform: uppercase; } 
        .isi { font-size: 24px; }
        .isi-kecil { font-size: 18px; color: #f1c40f; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1:
            st.markdown(f'<div class="box-info biru"><div class="judul">JENIS PRODUK A (KIRI)</div><div class="isi">{txt_a}</div></div>', unsafe_allow_html=True)
        with col_info_2:
            st.markdown(f'<div class="box-info merah"><div class="judul">JENIS PRODUK B (KANAN)</div><div class="isi">{txt_b}</div></div>', unsafe_allow_html=True)
        
        # --- INFO FORMULA (BARU) ---
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            st.markdown(f'<div class="box-info abu"><div class="judul">🧪 FORMULA BBKU</div><div class="isi-kecil">{f_bbku}</div></div>', unsafe_allow_html=True)
        with c_f2:
            st.markdown(f'<div class="box-info abu"><div class="judul">🔥 BAHAN BAKAR</div><div class="isi-kecil">{f_bakar}</div></div>', unsafe_allow_html=True)
        with c_f3:
            st.markdown(f'<div class="box-info abu"><div class="judul">🚛 LOADING</div><div class="isi-kecil">{f_loading}</div></div>', unsafe_allow_html=True)

        st.divider()

        # --- METRIK ---
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
