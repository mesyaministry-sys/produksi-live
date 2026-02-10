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
st.caption("Created : Mahesya") # <-- Sesuai Request

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
    # B. SMART SEARCH (SCANNER BARIS ATAS) 🕵️‍♂️
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 

    try:
        # Cari baris "9:00"
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_900 = matches[0]
            idx_start = idx_900
            
            # KUNCI PERBAIKAN: Fokus cari di SATU BARIS DI ATAS jam 9:00
            # Karena di Excel Anda, "Z 125" ada di atas data angka.
            row_target = idx_900 - 1 
            
            # --- FUNGSI VALIDASI KETAT ---
            def is_valid_product(text):
                t = str(text).strip()
                if len(t) < 2: return False
                
                # 1. Blacklist Header
                blacklist = ["nan", "none", "moisture", "particle", "mesh", "max", "min", "avg", 
                             "checker", "ok", "no", "shift", "time", "tonnage", "paraph", "%", "density"]
                if any(bad in t.lower() for bad in blacklist): return False
                
                # 2. Tolak Angka Murni & Range (Misal "1-5", "10.5")
                # Ini yang membuang "1-5" agar tidak terambil
                if re.match(r'^\d+-\d+$', t): return False # Tolak format 1-5
                if re.match(r'^[\d\.,]+$', t): return False # Tolak angka murni
                
                return True

            # --- SCAN LINE A (KIRI) ---
            # Area Kolom 6 s/d 11 (G-K) di Baris ATAS
            candidates_a = []
            vals_a = df_raw.iloc[row_target, 6:11].values.flatten()
            for v in vals_a:
                if is_valid_product(v):
                    candidates_a.append(str(v).strip())
            
            # Prioritas: Ambil yang ada ANGKA (Z 125)
            for c in candidates_a:
                if re.search(r'\d', c): 
                    produk_a = c; break
            # Jika tidak ketemu di baris atas, baru cek baris jam 9:00 (fallback)
            if produk_a == "-":
                vals_fallback = df_raw.iloc[idx_900, 6:11].values.flatten()
                for v in vals_fallback:
                    if is_valid_product(v) and re.search(r'\d', v):
                        produk_a = str(v).strip(); break

            # --- SCAN LINE B (KANAN) ---
            # Area Kolom 11 s/d 18 (L-R) di Baris ATAS
            candidates_b = []
            vals_b = df_raw.iloc[row_target, 11:18].values.flatten()
            for v in vals_b:
                if is_valid_product(v):
                    candidates_b.append(str(v).strip())

            # Prioritas: Ambil yang HURUF BESAR SEMUA (PRODUCT HOLD)
            for c in candidates_b:
                if c.isupper():
                    produk_b = c; break
            
    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL
    # ==========================================
    df = df_raw.iloc[idx_start:].copy() 
    nama_kolom = [
        "Jam Rotary A", "RM Rotary Moist A", "Rotary Moist A", 
        "Jam Rotary B", "RM Rotary Moist B", "Rotary Moist B", 
        "Jam Finish A", "Finish Moist A", "Finish Particle A", 
        "Tonnage A", "Checker A", 
        "Jam Finish B", "Finish Moist B", "Finish Particle B", 
        "Tonnage B", "Checker B", "Remarks"
    ]
    df = df.iloc[:, :len(nama_kolom)]
    if len(df.columns) < len(nama_kolom):
        for i in range(len(nama_kolom) - len(df.columns)): df[f"Col_{i}"] = np.nan
    df.columns = nama_kolom[:len(df.columns)]
    
    # BERSIHKAN ANGKA
    target_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                    "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    df_angka = df.copy()
    for col in target_angka:
        if col in df_angka.columns:
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    def hitung_tonnage(series):
        try:
            valid = series.dropna()
            if not valid.empty:
                val = str(valid.iloc[-1])
                if "-" in val: return float(val.split("-")[-1])
                elif val.replace('.','').isdigit(): return float(val)
        except: return 0
        return 0

    ton_a = hitung_tonnage(df["Tonnage A"])
    ton_b = hitung_tonnage(df["Tonnage B"]) 

    # ==========================================
    # E. TAMPILAN DASHBOARD
    # ==========================================
    if not df.empty:
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

        # ROTARY & FINISH
        st.subheader("🔥 Rotary Process (Gabungan A & B)")
        gab_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gab_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{gab_rm.mean():.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{gab_rot.mean():.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
        
        st.markdown("---")

        ca, cb = st.columns(2)
        with ca:
            st.markdown(f"#### 🅰️ LINE A")
            c1, c2 = st.columns(2)
            c1.metric("Moisture A", f"{df_angka['Finish Moist A'].mean():.2f}%")
            c2.metric("Particle Size A", f"{df_angka['Finish Particle A'].mean():.2f}")
            st.metric("Produksi Line A", f"{total_ton_a:.0f} TON")

        with cb:
            st.markdown(f"#### 🅱️ LINE B")
            c3, c4 = st.columns(2)
            c3.metric("Moisture B", f"{df_angka['Finish Moist B'].mean():.2f}%")
            c4.metric("Particle Size B", f"{df_angka['Finish Particle B'].mean():.2f}")
            st.metric("Produksi Line B", f"{total_ton_b:.0f} TON")

        st.divider()
        with st.expander("🔍 Lihat Tabel Data Mentah"):
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("Data kosong.")

except Exception as e:
    st.error(f"Error: {str(e)}")

