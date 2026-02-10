import streamlit as st
import pandas as pd
import numpy as np

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
    # A. BACA DATA RAW
    df_raw = pd.read_csv(url, header=None)

    # ==========================================
    # B. SMART SEARCH (CARI POSISI JAM 9:00) 🕵️‍♂️
    # ==========================================
    # Daripada menebak index baris (yang sering geser), kita cari baris "9:00" secara otomatis.
    
    # Default nilai jika tidak ketemu
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 # Fallback index

    try:
        # Cari baris dimana Kolom 0 berisi teks "9:00"
        # Kita scan 15 baris pertama saja biar cepat
        scan_area = df_raw.iloc[:15, 0].astype(str)
        matches = scan_area[scan_area.str.contains("9:00", na=False)].index
        
        if not matches.empty:
            idx_start = matches[0] # Ketemu! Ini nomor baris yang benar (misal: 6)
            
            # AMBIL PRODUK LINE A (Disebelah kanan jam 9:00)
            # Biasanya di Kolom I (Index 8). Kalau kosong, cek H (7).
            val_a = str(df_raw.iloc[idx_start, 8]) 
            if val_a == "nan" or val_a == "-" or val_a == "None":
                 val_a = str(df_raw.iloc[idx_start, 7]) # Cek kolom sebelahnya
            
            if val_a != "nan" and val_a != "-":
                 produk_a = val_a

            # AMBIL PRODUK LINE B (Disebelah kanan jauh)
            # Biasanya di Kolom M (Index 12).
            val_b = str(df_raw.iloc[idx_start, 12])
            if val_b == "nan" or val_b == "-" or val_b == "None":
                 val_b = str(df_raw.iloc[idx_start, 13])
            
            if val_b != "nan" and val_b != "-":
                 produk_b = val_b
    except:
        pass

    # ==========================================
    # C. OLAH DATA TABEL
    # ==========================================
    
    # Potong data mulai dari baris "9:00" tadi (minus 1 baris buat header dummy)
    # Tapi mapping kolom kita tetap pakai logika fixed agar rapi
    df = df_raw.iloc[idx_start:].copy() # Ambil dari jam 9 kebawah

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
    
    # Ambil 17 kolom & Rapikan
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
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    # Hitung Tonnage
    def hitung_tonnage(series_data):
        total = 0
        try:
            data_valid = series_data.dropna()
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
        
        # Style Kotak Warna
        st.markdown("""
        <style>
        .box-info { padding: 15px; border-radius: 8px; color: white; text-align: center; font-weight: bold; }
        .biru { background-color: #3498db; }
        .merah { background-color: #e74c3c; }
        .judul { font-size: 14px; opacity: 0.9; margin-bottom: 5px; }
        .isi { font-size: 24px; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1:
            if produk_a == "-" or produk_a == "nan": produk_a = "(Belum Diisi)"
            st.markdown(f"""
            <div class="box-info biru">
                <div class="judul">JENIS PRODUK LINE A (KIRI)</div>
                <div class="isi">{produk_a}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_info_2:
            if produk_b == "-" or produk_b == "nan": produk_b = "(Kosong)"
            st.markdown(f"""
            <div class="box-info merah">
                <div class="judul">JENIS PRODUK LINE B (KANAN)</div>
                <div class="isi">{produk_b}</div>
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
    st.error("Sedang memuat data... Jika lama, coba Refresh.")
