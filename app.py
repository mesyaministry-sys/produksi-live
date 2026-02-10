import streamlit as st
import pandas as pd
import numpy as np
import re # Library untuk pencarian teks

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
SHEET_ID = '1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY'

st.set_page_config(page_title="Monitoring Produksi", layout="wide")

# JUDUL SESUAI REQUEST
st.title("🏭 Monitoring Produksi Live")
st.caption("Created : Mahesya")

# ==========================================
# 1. MENU SAMPING
# ==========================================
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("📅 Pilih Periode")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) # Default tanggal 10

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW
    # Kita baca full dulu untuk mengambil header Z 125 & Product Hold
    df_raw = pd.read_csv(url, header=None)

    # === PERBAIKAN DI SINI (MENGAMBIL DATA DARI ROW 9 / H9 & M9) ===
    # Excel Row 9 = Python Index 8
    # Excel Col H = Python Index 7
    # Excel Col M = Python Index 12

    try:
        # Ambil Line A (H9:J9) -> Kita tembak H9 (Index 8, 7)
        val_a = str(df_raw.iloc[8, 7]) 

        # Jika H9 terbaca 'nan' (kosong), coba geser dikit ke I9 (Index 8, 8) jaga-jaga merge cell
        if val_a == "nan" or val_a == "-":
             val_a = str(df_raw.iloc[8, 8])

        if val_a == "nan" or val_a == "-":
             produk_a = "-"
        else:
             produk_a = val_a

        # Ambil Line B (M9:O9) -> Kita tembak M9 (Index 8, 12)
        val_b = str(df_raw.iloc[8, 12])
        if val_b == "nan" or val_b == "-":
             produk_b = "-"
        else:
             produk_b = val_b
    except:
        produk_a = "-"
        produk_b = "-"
    # ==============================================================

    # B. POTONG BARIS (Mulai dari baris ke-7 untuk data angka)
    df = df_raw.iloc[6:].copy()

    # C. DEFINISI KOLOM (MAPPING POSISI EXCEL)
    nama_kolom = [
        "Jam Rotary A",         # 0
        "RM Rotary Moist A",    # 1
        "Rotary Moist A",       # 2
        "Jam Rotary B",         # 3
        "RM Rotary Moist B",    # 4
        "Rotary Moist B",       # 5
        "Jam Finish A",         # 6
        "Finish Moist A",       # 7
        "Finish Particle A",    # 8  <-- POSISI PANAH MERAH (Z 211)
        "Tonnage A",            # 9
        "Checker A",            # 10
        "Jam Finish B",         # 11 
        "Finish Moist B",       # 12
        "Finish Particle B",    # 13 <-- POSISI PANAH HIJAU
        "Tonnage B",            # 14
        "Checker B",            # 15
        "Remarks"               # 16
    ]

    # Ambil 17 kolom pertama
    df = df.iloc[:, :len(nama_kolom)]

    # Tambal kolom jika kurang (antisipasi error)
    if len(df.columns) < len(nama_kolom):
        for i in range(len(nama_kolom) - len(df.columns)):
            df[f"Col_Kosong_{i}"] = np.nan

    df.columns = nama_kolom[:len(df.columns)]

    # ==========================================
    # D. (LOGIKA DETEKSI SUDAH DIPINDAH KE ATAS)
    # ==========================================

    # E. BERSIHKAN ANGKA (Persiapan Hitung)
    # ==========================================
    target_angka = [
        "RM Rotary Moist A", "Rotary Moist A", 
        "RM Rotary Moist B", "Rotary Moist B", 
        "Finish Moist A", "Finish Particle A",
        "Finish Moist B", "Finish Particle B"
    ]

    # Buat copy khusus untuk hitungan angka
    df_angka = df.copy()

    for col in target_angka:
        if col in df_angka.columns:
            # Ganti koma jadi titik
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            # Paksa jadi angka (Teks produk Z 211 akan jadi NaN disini, aman untuk rata-rata)
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    # F. HITUNG TONNAGE
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
    # 3. TAMPILAN DASHBOARD (LAYOUT RAPI)
    # ==========================================

    if not df.empty:
        st.success(f"✅ Data Tanggal {pilihan_sheet} Berhasil Ditarik!")

        # --- BAGIAN 1: INFO PRODUK (PANAH BIRU) ---
        # Kita buat kotak khusus info produk di atas agar menonjol
        st.markdown("### 🏷️ Informasi Batch Produksi")

        col_info_1, col_info_2 = st.columns(2)

        # KOTAK KIRI (LINE A)
        with col_info_1:
            # Tampilkan Produk A yang diambil dari Header tadi
            st.info(f"**Jenis Produk Line A:** {produk_a}")

        # KOTAK KANAN (LINE B)
        with col_info_2:
            # Tampilkan Produk B yang diambil dari Header tadi
            # Warna beda dikit biar terlihat pemisahnya
            if produk_b == "-" or produk_b == "nan":
                st.warning(f"**Jenis Produk Line B:** -")
            else:
                st.success(f"**Jenis Produk Line B:** {produk_b}")

        st.divider()

        # --- BAGIAN 2: ROTARY (GABUNGAN) ---
        st.subheader("🔥 Rotary Process (Gabungan A & B)")

        gabungan_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gabungan_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])

        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{gabungan_rm.mean():.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{gabungan_rot.mean():.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")

        st.markdown("---")

        # --- BAGIAN 3: FINISH PRODUCT (TERPISAH A & B) ---
        col_a, col_b = st.columns(2)

        # === LINE A (KIRI) ===
        with col_a:
            st.markdown(f"#### 🅰️ LINE A ({produk_a})")
            # Tampilkan data hanya jika ada isinya
            if df_angka['Finish Moist A'].isnull().all():
                 st.write("Data Line A Kosong")
            else:
                c1, c2 = st.columns(2)
                c1.metric("Moisture A", f"{df_angka['Finish Moist A'].mean():.2f}%")
                c2.metric("Particle Size A", f"{df_angka['Finish Particle A'].mean():.2f}")
                st.metric("Produksi Line A", f"{total_ton_a:.0f} TON")

        # === LINE B (KANAN) ===
        with col_b:
            st.markdown(f"#### 🅱️ LINE B ({produk_b})")
            # Cek apakah Line B ada datanya
            if df_angka['Finish Moist B'].isnull().all():
                st.caption("🚫 Tidak ada aktivitas produksi di Line B")
            else:
                c3, c4 = st.columns(2)
                c3.metric("Moisture B", f"{df_angka['Finish Moist B'].mean():.2f}%")
                c4.metric("Particle Size B", f"{df_angka['Finish Particle B'].mean():.2f}")
                st.metric("Produksi Line B", f"{total_ton_b:.0f} TON")

        st.divider()

        # --- TABEL DATA ---
        with st.expander("🔍 Lihat Tabel Data Mentah"):
            st.dataframe(df, use_container_width=True)

    else:
        st.warning("Data kosong.")

except Exception as e:
    st.error("Terjadi masalah teknis.")
    with st.expander("Lihat Error"):
        st.write(e)
