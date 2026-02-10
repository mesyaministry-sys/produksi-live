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
st.caption("Created : Mahesya | Versi: Tembak Jitu (Un-Merged)")

# ==========================================
# 1. MENU SAMPING
# ==========================================
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("📅 Pilih Periode")
    # Default ke tanggal 2 sesuai screenshot Anda
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=1) 
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # Baca data sebagai string agar aman
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ==========================================
    # 🚨 VALIDASI TANGGAL (VERSI LEMBUT) 🚨
    # ==========================================
    # Cek apakah sheet yang dikirim Google sesuai permintaan
    # Kita cari angka tanggal di area header (Baris 1-5, Kolom A)
    tanggal_terbaca = "Tidak Terdeteksi"
    
    try:
        # Ambil area pojok kiri atas
        header_text = str(df_raw.iloc[0:5, 0].values).lower()
        # Cari angka setelah kata "date" atau angka tunggal di awal
        matches = re.findall(r'date\s*[:\.]\s*(\d+)', header_text)
        if not matches:
             matches = re.findall(r'\b(\d+)-[a-z]{3}', header_text) # Format: 2-Jan
        
        if matches:
            tanggal_terbaca = matches[0]
    except:
        pass

    # Jika beda jauh (misal pilih 10 tapi isinya 2), kasih warning tapi JANGAN STOP
    if tanggal_terbaca != "Tidak Terdeteksi" and tanggal_terbaca != pilihan_sheet:
        st.warning(f"⚠️ **Peringatan:** Anda memilih Tanggal **{pilihan_sheet}**, tapi data Excel menunjukkan Tanggal **{tanggal_terbaca}**. (Kemungkinan sheet tanggal {pilihan_sheet} belum ada).")

    # ==========================================
    # 🎯 KOORDINAT TEMBAK JITU (INDEXING)
    # ==========================================
    
    # Cari Baris Jam 9:00
    # Berdasarkan gambar 05.jpg, jam 9:00 ada di baris ke-9 (Index 8 di Python)
    # Tapi biar aman, kita cari text "9:00"
    scan_col = df_raw.iloc[:, 0].astype(str)
    matches = scan_col[scan_col.str.contains(r"9[:\.]00")].index
    
    if matches.empty:
        st.error("❌ Data jam 9:00 tidak ditemukan! Pastikan format jam '9:00' ada di kolom paling kiri.")
        st.stop()
        
    idx_row = matches[0] # Ini adalah baris tempat Z 125 berada (Baris 9 di Excel)

    # --- AMBIL PRODUK LINE A (KIRI) ---
    # Di Excel Kolom J adalah kolom ke-10. Di Python indexnya 9.
    # Namun karena ada kolom tersembunyi/merge sebelumnya, kita scan range KECIL di kolom I, J, K (Index 8, 9, 10)
    
    produk_a = "-"
    
    # Kita ambil 3 kolom di baris jam 9:00 (Kolom I, J, K)
    # Kolom I = Index 8
    # Kolom J = Index 9 (Target Utama "Z 125")
    # Kolom K = Index 10
    candidates_a = df_raw.iloc[idx_row, 8:11].values.flatten()
    
    for c in candidates_a:
        val = str(c).strip()
        # Syarat: Bukan kosong, bukan angka murni, bukan "max"/"min"
        if len(val) > 1 and not val.replace('.','').isdigit():
            if "max" not in val.lower() and "min" not in val.lower():
                produk_a = val
                break # Ketemu langsung stop

    # --- AMBIL PRODUK LINE B (KANAN) ---
    # Biasanya di kolom N / O (Index 13/14)
    # Kita scan range kolom M, N, O, P (Index 12 - 15)
    
    produk_b = "-"
    candidates_b = df_raw.iloc[idx_row, 12:16].values.flatten()
    
    for c in candidates_b:
        val = str(c).strip()
        if len(val) > 1 and not val.replace('.','').isdigit():
             if "max" not in val.lower() and "min" not in val.lower() and "juan" not in val.lower():
                produk_b = val
                break

    # ==========================================
    # OLAH DATA ANGKA
    # ==========================================
    
    # Data angka mulai dari baris jam 9:00
    df = df_raw.iloc[idx_row:].copy()
    
    # Mapping Kolom Manual (Sesuai Gambar Excel Anda)
    # 0: Jam
    # 1: RM Rotary Moist A (39,51)
    # 2: Rotary Moist A (-)
    # 3: Jam Rotary B (21:00)
    # 4: RM Rotary Moist B
    # 5: Rotary Moist B (5,49)
    # ... lompat ...
    # 7: Moisture A (11,74) -> Kolom H
    # 8: Particle A (83,35) -> Kolom I
    # 9: Tonnage A (1-5)    -> Kolom J (Isinya Produk Z 125 di baris pertama, angka di bawahnya)
    
    # KITA PERBAIKI MAPPING KOLOM AGAR PRESISI
    # Kita ambil kolom index tertentu saja dari CSV
    
    selected_data = pd.DataFrame()
    selected_data["Jam"] = df.iloc[:, 0]
    
    # Rotary A (Kolom B, C -> Index 1, 2)
    selected_data["RM Rotary Moist A"] = df.iloc[:, 1]
    selected_data["Rotary Moist A"] = df.iloc[:, 2]
    
    # Rotary B (Kolom E, F -> Index 4, 5)
    selected_data["RM Rotary Moist B"] = df.iloc[:, 4]
    selected_data["Rotary Moist B"] = df.iloc[:, 5]
    
    # Finish Product A (Kolom H, I -> Index 7, 8)
    selected_data["Finish Moist A"] = df.iloc[:, 7]
    selected_data["Finish Particle A"] = df.iloc[:, 8]
    selected_data["Tonnage A"] = df.iloc[:, 9] # Kolom J
    
    # Finish Product B (Perkiraan Kolom M, N -> Index 12, 13)
    # Cek dulu apakah index 12/13 ada isinya
    if df.shape[1] > 13:
        selected_data["Finish Moist B"] = df.iloc[:, 12]
        selected_data["Finish Particle B"] = df.iloc[:, 13]
        selected_data["Tonnage B"] = df.iloc[:, 14]
    else:
        selected_data["Finish Moist B"] = 0
        selected_data["Finish Particle B"] = 0
        selected_data["Tonnage B"] = 0

    # BERSIHKAN ANGKA (Convert text "39,51" to float 39.51)
    cols_num = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B",
                "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    df_clean = selected_data.copy()
    
    for c in cols_num:
        if c in df_clean.columns:
            # Ganti koma jadi titik
            df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
            # Hapus baris Z 125 (karena itu teks) biar jadi angka
            df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    # HITUNG TONNAGE (Total Harian)
    def sum_tonnage(series):
        total = 0
        # Ambil data yang valid (angka atau range 1-5)
        valid_rows = series[~series.astype(str).str.contains(r'[a-zA-Z]', regex=True)] # Buang yang ada huruf (Z 125)
        
        if not valid_rows.empty:
            last_val = str(valid_rows.iloc[-1]) # Ambil angka paling bawah
            # Jika format "26-34", ambil 34
            if "-" in last_val:
                try:
                    total = float(last_val.split("-")[-1])
                except: pass
            # Jika angka biasa
            elif last_val.replace('.','').isdigit():
                total = float(last_val)
        return total

    ton_a = sum_tonnage(df_clean["Tonnage A"])
    ton_b = sum_tonnage(df_clean["Tonnage B"])

    # ==========================================
    # TAMPILAN DASHBOARD
    # ==========================================
    st.success(f"✅ Data Tanggal {pilihan_sheet} Berhasil Ditarik!")
    
    st.markdown("### 🏷️ Informasi Batch Produksi")
    c1, c2 = st.columns(2)
    
    # Kotak Info Produk
    txt_a = produk_a if produk_a not in ["-", ""] else "(Belum Diisi)"
    txt_b = produk_b if produk_b not in ["-", ""] else "(Kosong)"
    
    st.markdown("""
    <style>
    .k-biru { background-color: #3498db; padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;}
    .k-merah { background-color: #e74c3c; padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 10px;}
    .h-text { font-size: 16px; font-weight: bold; opacity: 0.9; }
    .v-text { font-size: 28px; font-weight: 800; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

    with c1:
        st.markdown(f'<div class="k-biru"><div class="h-text">JENIS PRODUK A (KIRI)</div><div class="v-text">{txt_a}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="k-merah"><div class="h-text">JENIS PRODUK B (KANAN)</div><div class="v-text">{txt_b}</div></div>', unsafe_allow_html=True)

    st.divider()
    
    # METRIK UTAMA
    st.subheader("🔥 Rotary Process (Gabungan)")
    
    # Rata-rata Gabungan
    rm_avg = pd.concat([df_clean["RM Rotary Moist A"], df_clean["RM Rotary Moist B"]]).mean()
    rot_avg = pd.concat([df_clean["Rotary Moist A"], df_clean["Rotary Moist B"]]).mean()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("RM Rotary Moist (Avg)", f"{rm_avg:.2f}%")
    col2.metric("Rotary Moist (Avg)", f"{rot_avg:.2f}%")
    col3.metric("Total Output Harian", f"{ton_a + ton_b:.0f} TON")
    
    st.markdown("---")
    
    # DETAIL PER LINE
    ca, cb = st.columns(2)
    
    with ca:
        st.markdown(f"#### 🅰️ LINE A ({txt_a})")
        m1, m2 = st.columns(2)
        m1.metric("Moisture", f"{df_clean['Finish Moist A'].mean():.2f}%")
        m2.metric("Particle (200 Mesh)", f"{df_clean['Finish Particle A'].mean():.2f}")
        st.metric("Output Line A", f"{ton_a:.0f} TON")
        
    with cb:
        st.markdown(f"#### 🅱️ LINE B ({txt_b})")
        m3, m4 = st.columns(2)
        m3.metric("Moisture", f"{df_clean['Finish Moist B'].mean():.2f}%")
        m4.metric("Particle (200 Mesh)", f"{df_clean['Finish Particle B'].mean():.2f}")
        st.metric("Output Line B", f"{ton_b:.0f} TON")

    with st.expander("🔍 Lihat Data Mentah (Tabel)"):
        st.dataframe(selected_data)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
