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
    # B. PENCARIAN DATA (FORMULA & PRODUK)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    
    # Default Formula
    f_bbku = "-"
    f_bakar = "-"
    f_loading = "-"
    
    idx_start = 6 

    try:
        # --- 1. CARI FORMULA (SCANNER BARIS PENUH) ---
        # Kita scan baris 25 sampai 45 (Area Bawah)
        # Kita gabungkan semua kolom di baris itu jadi satu kalimat panjang untuk dicari
        for i in range(25, 45):
            if i >= len(df_raw): break
            
            # Ambil satu baris penuh, gabung jadi text
            row_text = " ".join(df_raw.iloc[i].astype(str).values).upper()
            
            # Bersihkan karakter aneh
            row_text = row_text.replace("_", " ").replace("  ", " ")
            
            if "FORMULA BBKU" in row_text or "BBKU" in row_text:
                # Cari teks setelah titik dua (:)
                if ":" in row_text:
                    temp = row_text.split(":")[-1].strip()
                    # Ambil kata-kata awal saja (misal SMBE Z 125) sampai ketemu kata lain/kosong
                    f_bbku = temp.split("FORMULA")[0].strip() # Jaga-jaga kalau nyambung
                    
            if "BAHAN BAKAR" in row_text:
                if ":" in row_text:
                    temp = row_text.split(":")[-1].strip()
                    f_bakar = temp.split("LOADING")[0].strip()
            
            if "LOADING" in row_text:
                if ":" in row_text:
                    f_loading = row_text.split(":")[-1].strip()

        # Bersihkan hasil (kadang ada sisa koma/nan)
        f_bbku = f_bbku.replace("NAN", "").replace(",", "").strip()
        f_bakar = f_bakar.replace("NAN", "").replace(",", "").strip()
        f_loading = f_loading.replace("NAN", "").replace(",", "").strip()
        
        if f_bbku == "": f_bbku = "-"
        if f_bakar == "": f_bakar = "-"
        if f_loading == "": f_loading = "-"


        # --- 2. CARI POSISI JAM 9:00 ---
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0] # Baris Jam 9:00
            idx_atas = idx_start - 1
            
            # --- FUNGSI FILTER PRODUK ---
            def is_valid(val):
                t = str(val).strip()
                if len(t) < 2: return False
                # Tolak jika angka murni / range / header
                if t.replace('.','').replace(',','').isdigit(): return False
                if re.match(r'^\d+-\d+$', t): return False
                if any(x in t.lower() for x in ["moisture", "particle", "mesh", "max", "min"]): return False
                return True

            # --- CARI PRODUK A (Fokus Area Kolom 8-9) ---
            # Prioritas 1: Baris ATAS Jam 9, Kolom 8 (Sesuai Request)
            kandidat_a = [
                df_raw.iloc[idx_atas, 8],   # Index 8 (I) - Baris Atas
                df_raw.iloc[idx_atas, 9],   # Index 9 (J) - Baris Atas
                df_raw.iloc[idx_start, 8],  # Index 8 (I) - Baris 9:00
            ]
            
            for k in kandidat_a:
                if is_valid(k):
                    produk_a = str(k).strip()
                    break

            # --- CARI PRODUK B (Fokus Area Kolom 13-14) ---
            # Prioritas 1: Baris ATAS Jam 9, Kolom 13 (Sesuai Request)
            kandidat_b = [
                df_raw.iloc[idx_atas, 13],  # Index 13 (N) - Baris Atas
                df_raw.iloc[idx_atas, 14],  # Index 14 (O) - Baris Atas
                df_raw.iloc[idx_start, 13], # Index 13 (N) - Baris 9:00
            ]
            
            for k in kandidat_b:
                if is_valid(k):
                    produk_b = str(k).strip()
                    break

    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL (DIPERBAIKI)
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
            # Buang text produk jika masuk kolom tonnage
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

        # CSS Card Style
        st.markdown("""
        <style>
        .card { 
            padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .bg-blue { background: linear-gradient(135deg, #3498db, #2980b9); }
        .bg-red { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .bg-dark { background-color: #2c3e50; border: 1px solid #34495e; padding: 15px; border-radius: 8px; }
        
        .label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; margin-bottom: 5px; color: #ecf0f1; }
        .value { font-size: 24px; font-weight: 800; }
        .value-small { font-size: 18px; font-weight: bold; color: #5dade2; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1:
            st.markdown(f'<div class="card bg-blue"><div class="label">JENIS PRODUK A (KIRI)</div><div class="value">{txt_a}</div></div>', unsafe_allow_html=True)
        with col_info_2:
            st.markdown(f'<div class="card bg-red"><div class="label">JENIS PRODUK B (KANAN)</div><div class="value">{txt_b}</div></div>', unsafe_allow_html=True)
        
        # --- INFO FORMULA (TAMPILAN SESUAI REQUEST) ---
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">FORMULA BBKU</div><div class="value-small">{f_bbku}</div></div>', unsafe_allow_html=True)
        with c_f2:
            st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">BAHAN BAKAR</div><div class="value-small">{f_bakar}</div></div>', unsafe_allow_html=True)
        with c_f3:
            st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">LOADING</div><div class="value-small">{f_loading}</div></div>', unsafe_allow_html=True)

        st.divider()

        # --- METRIK ---
        st.subheader("🔥 Rotary Process (Gabungan A & B)")
        
        # Hitung Mean (Abaikan 0)
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
