import streamlit as st
import pandas as pd
import numpy as np
import re

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
SHEET_ID = '1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY'

st.set_page_config(page_title="Monitoring Produksi", layout="wide")
st.title("🏭 Monitoring Produksi Live")
st.caption("Created : Mahesya")

# ==========================================
# 1. MENU SAMPING
# ==========================================
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("📅 Pilih Periode")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW (PENTING: dtype=str agar Z 125 terbaca sebagai teks)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ==========================================
    # B. SMART SEARCH (SCANNER AREA JAM 9:00) 🕵️‍♂️
    # ==========================================
    
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 # Fallback index

    try:
        # 1. Cari baris "9:00"
        scan_area = df_raw.iloc[:25, 0].astype(str)
        # Regex mencari 9:00, 09:00, atau 9.00
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0] # Baris Jam 9:00
            
            # --- FUNGSI VALIDASI PRODUK ---
            def is_valid_product(text):
                t = str(text).strip()
                # 1. Tolak jika terlalu pendek/kosong
                if len(t) < 2: return False
                
                # 2. Blacklist kata-kata sampah
                blacklist = ["nan", "none", "moisture", "particle", "mesh", "max", "min", "avg", 
                             "checker", "ok", "no", "shift", "time", "tonnage"]
                if any(bad in t.lower() for bad in blacklist): return False
                
                # 3. Tolak jika isinya CUMA ANGKA (misal "10.5" atau "12,1")
                # Hapus titik dan koma, cek apakah angka semua
                clean_num = t.replace('.', '').replace(',', '')
                if clean_num.isdigit(): return False
                
                return True

            # --- SCAN LINE A (KIRI) ---
            # Kita scan Kolom 6, 7, 8, 9, 10 (Area G-K)
            candidates_a = []
            vals_a = df_raw.iloc[idx_start, 6:11].values.flatten()
            for v in vals_a:
                if is_valid_product(v):
                    candidates_a.append(str(v).strip())
            
            # Prioritas: Ambil yang ada ANGKA-nya (Z 125)
            for c in candidates_a:
                if re.search(r'\d', c): 
                    produk_a = c; break
            if produk_a == "-" and candidates_a: produk_a = candidates_a[0]

            # --- SCAN LINE B (KANAN) ---
            # Kita scan Kolom 11, 12, 13, 14, 15 (Area L-P)
            candidates_b = []
            vals_b = df_raw.iloc[idx_start, 11:16].values.flatten()
            for v in vals_b:
                if is_valid_product(v):
                    candidates_b.append(str(v).strip())

            # Prioritas: Ambil yang HURUF BESAR SEMUA (PRODUCT HOLD)
            for c in candidates_b:
                if c.isupper():
                    produk_b = c; break
            if produk_b == "-" and candidates_b: produk_b = candidates_b[0]
            
    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL
    # ==========================================
    
    # Ambil data dari baris jam 9:00 ke bawah
    df = df_raw.iloc[idx_start:].copy() 

    nama_kolom = [
        "Jam Rotary A",         # 0
        "RM Rotary Moist A",    # 1
        "Rotary Moist A",       # 2
        "Jam Rotary B",         # 3
        "RM Rotary Moist B",    # 4
        "Rotary Moist B",       # 5
        "Jam Finish A",         # 6
        "Finish Moist A",       # 7
        "Finish Particle A",    # 8 
        "Tonnage A",            # 9
        "Checker A",            # 10
        "Jam Finish B",         # 11 
        "Finish Moist B",       # 12
        "Finish Particle B",    # 13
        "Tonnage B",            # 14
        "Checker B",            # 15
        "Remarks"               # 16
    ]
    
    # Rapikan Kolom
    df = df.iloc[:, :len(nama_kolom)]
    if len(df.columns) < len(nama_kolom):
        for i in range(len(nama_kolom) - len(df.columns)):
            df[f"Col_{i}"] = np.nan
    df.columns = nama_kolom[:len(df.columns)]
    
    # ==========================================
    # D. BERSIHKAN ANGKA
    # ==========================================
    target_angka = [
        "RM Rotary Moist A", "Rotary Moist A", 
        "RM Rotary Moist B", "Rotary Moist B", 
        "Finish Moist A", "Finish Particle A",
        "Finish Moist B", "Finish Particle B"
    ]
    
    df_angka = df.copy()
    for col in target_angka:
        if col in df_angka.columns:
            # Replace koma dengan titik
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            # Ubah ke numerik, error (seperti teks 'Z 125') jadi NaN
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    # Hitung Tonnage
    def hitung_tonnage(series_data):
        total = 0
        try:
            # Filter data valid (bukan strip/kosong/nan)
            data_valid = series_data[~series_data.isin(["-", "", "nan", "None"])].dropna()
            if not data_valid.empty:
                last_val = str(data_valid.iloc[-1])
                if "-" in last_val:
                    total = float(last_val.split("-")[-1])
                elif last_val.replace('.','').isdigit():
                    total = float(last_val)
        except:
            total = 0
        return total

    total_ton_a = hitung_tonnage(df["Tonnage A"])
    total_ton_b = hitung_tonnage(df["Tonnage B"]) 
    total_gabungan = total_ton_a + total_ton_b

    # ==========================================
    # E. TAMPILAN DASHBOARD
    # ==========================================
    
    if not df.empty:
        st.success(f"✅ Data Tanggal {pilihan_sheet} Berhasil Ditarik!")
        
        # --- INFO PRODUK (HASIL SMART SEARCH) ---
        st.markdown("### 🏷️ Informasi Batch Produksi")
        
        col_info_1, col_info_2 = st.columns(2)
        
        # CSS Styling
        st.markdown("""
        <style>
        .box-info { padding: 20px; border-radius: 10px; color: white; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); }
        .biru { background-color: #3498db; }
        .merah { background-color: #e74c3c; }
        .judul { font-size: 14px; opacity: 0.9; margin-bottom: 5px; font-weight: bold; }
        .isi { font-size: 24px; font-weight: 800; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1:
            txt_a = produk_a if produk_a not in ["-", "nan", ""] else "(Belum Diisi)"
            st.markdown(f"""
            <div class="box-info biru">
                <div class="judul">JENIS PRODUK LINE A (KIRI)</div>
                <div class="isi">{txt_a}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_info_2:
            txt_b = produk_b if produk_b not in ["-", "nan", ""] else "(Kosong)"
            st.markdown(f"""
            <div class="box-info merah">
                <div class="judul">JENIS PRODUK LINE B (KANAN)</div>
                <div class="isi">{txt_b}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()

        # --- ROTARY PROCESS ---
        st.subheader("🔥 Rotary Process (Gabungan A & B)")
        
        gabungan_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gabungan_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{gabungan_rm.mean():.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{gabungan_rot.mean():.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
        
        st.markdown("---")

        # --- FINISH PRODUCT ---
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(f"#### 🅰️ LINE A")
            if df_angka['Finish Moist A'].isnull().all():
                 st.info("Menunggu data masuk...")
            else:
                c1, c2 = st.columns(2)
                c1.metric("Moisture A", f"{df_angka['Finish Moist A'].mean():.2f}%")
                c2.metric("Particle Size A", f"{df_angka['Finish Particle A'].mean():.2f}")
                st.metric("Produksi Line A", f"{total_ton_a:.0f} TON")

        with col_b:
            st.markdown(f"#### 🅱️ LINE B")
            if df_angka['Finish Moist B'].isnull().all():
                st.info("Tidak ada produksi.")
            else:
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
    st.error(f"Sedang memuat data... ({e})")
