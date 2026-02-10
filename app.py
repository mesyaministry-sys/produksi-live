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
st.caption("Created : Mahesya | Versi: Final Strict")

# ==========================================
# 1. MENU SAMPING
# ==========================================
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("📅 Pilih Periode")
    # Default ke tanggal 10 untuk tes
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. FUNGSI PEMBERSIH & PENCARI
# ==========================================

# Fungsi untuk membuang sampah dan hanya mengambil produk valid
def filter_produk(text):
    if not isinstance(text, str): return False
    t = text.strip()
    
    # 1. Buang yang terlalu pendek atau kosong
    if len(t) < 2: return False
    
    # 2. Buang kata-kata terlarang (Blacklist)
    blacklist = ["nan", "none", "null", "moisture", "particle", "mesh", 
                 "time", "tonnage", "checker", "ok", "no", "shift", 
                 "max", "min", "avg", "%", "density", "temp", "speed"]
    if any(bad in t.lower() for bad in blacklist): return False

    # 3. Buang jika isinya CUMA ANGKA (misal: "11.36" atau "10")
    # Hapus titik dan koma, cek apakah sisa angka semua
    cek_angka = t.replace('.', '').replace(',', '').replace('-', '').strip()
    if cek_angka.isdigit(): return False

    # 4. TANGKAP PRODUK (Logika Prioritas)
    
    # A. Cek Huruf Besar Semua (PRODUCT HOLD BLEND) -> TERIMA
    # Pastikan panjang minimal 3 huruf agar "OK" tidak masuk
    if t.isupper() and len(t) > 3:
        return True
        
    # B. Cek Kode Kombinasi (Z 125, Z 211) -> TERIMA
    # Harus ada Huruf DAN ada Angka
    has_letter = bool(re.search('[a-zA-Z]', t))
    has_digit = bool(re.search('\d', t))
    if has_letter and has_digit:
        return True

    # C. Buang Nama Orang (Biasanya Title Case: "Juan", "Phadla", "Dian")
    # Jika huruf depannya besar, tapi sisanya kecil, dan TIDAK ada angka -> BUANG
    if t[0].isupper() and not t.isupper() and not has_digit:
        return False
        
    return False

# ==========================================
# 3. PROSES DATA UTAMA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # Baca data sebagai TEKS MURNI (dtype=str) agar "11,36" tidak jadi angka
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # --- 🚨 VALIDASI TANGGAL (SATPOL PP) 🚨 ---
    # Cari tulisan tanggal di 10 baris pertama, kolom A-F
    tanggal_excel_ditemukan = False
    info_tanggal_excel = "Tidak Terbaca"

    # Scan area kotak 10x10 di pojok kiri atas
    scan_header = df_raw.iloc[:10, :10].values.flatten()
    
    for cell in scan_header:
        txt = str(cell).lower()
        if "date" in txt or "tanggal" in txt:
            # Ambil angka dari teks (misal "Date: 6 Jan" -> ambil "6")
            angka = re.findall(r'\d+', txt)
            if angka:
                info_tanggal_excel = angka[0] # Ambil angka pertama
                # Bandingkan dengan pilihan user
                if int(info_tanggal_excel) == int(pilihan_sheet):
                    tanggal_excel_ditemukan = True
                break
    
    # JIKA TANGGAL SALAH -> MATIKAN APLIKASI
    if not tanggal_excel_ditemukan:
        st.error(f"⛔ STOP! DATA TIDAK SESUAI.")
        st.markdown(f"""
        **Analisa Error:**
        * Anda meminta data Tanggal: **{pilihan_sheet}**
        * Tetapi File Excel memberikan data Tanggal: **{info_tanggal_excel}**
        
        **Penyebab:**
        Sheet untuk tanggal **{pilihan_sheet}** kemungkinan **BELUM DIBUAT** atau **KOSONG** di file Excel, 
        sehingga Google mengirimkan sheet lain (default).
        """)
        st.stop() # Berhenti total

    # --- 🕵️‍♂️ PENCARIAN BARIS JAM 9:00 ---
    scan_col_a = df_raw.iloc[:30, 0].astype(str)
    # Cari 9:00 atau 09:00 atau 9.00
    matches = scan_col_a[scan_col_a.str.contains(r"\b0?9[:\.]00", regex=True)].index
    
    if matches.empty:
        st.warning("⚠️ Jam 9:00 tidak ditemukan di kolom paling kiri.")
        st.stop()

    idx_start = matches[0]
    
    # --- 🔎 DETEKSI PRODUK (SCANNER MELEBAR) ---
    produk_a = "-"
    produk_b = "-"
    
    # Ambil 3 baris (jam 9:00, baris atasnya, baris bawahnya) untuk jaga-jaga merge cell
    rows_to_check = [idx_start, idx_start-1, idx_start+1]
    
    # SCAN LINE A (Kolom G sampai K / Index 6-10)
    calon_produk_a = []
    for r in rows_to_check:
        # Ambil data dari kolom 6, 7, 8, 9, 10
        vals = df_raw.iloc[r, 6:11].values.flatten()
        for v in vals:
            if filter_produk(str(v)):
                calon_produk_a.append(str(v).strip())
    
    # Ambil yang pertama ditemukan
    if calon_produk_a: produk_a = calon_produk_a[0]

    # SCAN LINE B (Kolom L sampai Q / Index 11-16)
    calon_produk_b = []
    for r in rows_to_check:
        # Ambil data dari kolom 11 s/d 16
        vals = df_raw.iloc[r, 11:17].values.flatten()
        for v in vals:
            if filter_produk(str(v)):
                calon_produk_b.append(str(v).strip())

    if calon_produk_b: produk_b = calon_produk_b[0]

    # --- OLAH DATA ANGKA (SEPERTI BIASA) ---
    df = df_raw.iloc[idx_start:].copy()
    
    # Setup Nama Kolom
    cols = [
        "Jam Rotary A", "RM Rotary Moist A", "Rotary Moist A", 
        "Jam Rotary B", "RM Rotary Moist B", "Rotary Moist B", 
        "Jam Finish A", "Finish Moist A", "Finish Particle A", 
        "Tonnage A", "Checker A", 
        "Jam Finish B", "Finish Moist B", "Finish Particle B", 
        "Tonnage B", "Checker B", "Remarks"
    ]
    df = df.iloc[:, :len(cols)]
    df.columns = cols[:len(df.columns)]
    
    # Bersihkan Angka
    target_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                    "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    df_angka = df.copy()
    for col in target_angka:
        if col in df_angka.columns:
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    # Hitung Tonnage
    def get_ton(series):
        try:
            valid = series[~series.isin(["-", "", "nan"])].dropna()
            if not valid.empty:
                val = str(valid.iloc[-1])
                if "-" in val: return float(val.split("-")[-1])
                return float(val)
        except: return 0
        return 0

    total_a = get_ton(df["Tonnage A"])
    total_b = get_ton(df["Tonnage B"])

    # --- TAMPILAN DASHBOARD ---
    st.success(f"✅ Data Valid: Tanggal {pilihan_sheet}")
    
    # INFO PRODUK
    st.markdown("### 🏷️ Informasi Batch Produksi")
    c1, c2 = st.columns(2)
    
    # Style Kotak
    st.markdown("""
    <style>
    .k-biru { background-color: #3498db; padding: 15px; border-radius: 10px; text-align: center; color: white; }
    .k-merah { background-color: #e74c3c; padding: 15px; border-radius: 10px; text-align: center; color: white; }
    .lbl { font-size: 14px; font-weight: bold; opacity: 0.8; }
    .val { font-size: 24px; font-weight: 800; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)
    
    txt_a = produk_a if produk_a != "-" else "(Belum Diisi)"
    txt_b = produk_b if produk_b != "-" else "(Kosong)"
    
    with c1:
        st.markdown(f'<div class="k-biru"><div class="lbl">LINE A (KIRI)</div><div class="val">{txt_a}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="k-merah"><div class="lbl">LINE B (KANAN)</div><div class="val">{txt_b}</div></div>', unsafe_allow_html=True)
        
    st.divider()
    
    # METRIK
    st.subheader("🔥 Rotary Process")
    gab_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
    gab_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
    
    k1, k2, k3 = st.columns(3)
    k1.metric("RM Rotary Avg", f"{gab_rm.mean():.2f}%")
    k2.metric("Rotary Avg", f"{gab_rot.mean():.2f}%")
    k3.metric("Total Output", f"{total_a + total_b:.0f} TON")
    
    st.markdown("---")
    
    ca, cb = st.columns(2)
    with ca:
        st.markdown("#### 🅰️ LINE A")
        c_1, c_2 = st.columns(2)
        c_1.metric("Moisture", f"{df_angka['Finish Moist A'].mean():.2f}%")
        c_2.metric("Particle", f"{df_angka['Finish Particle A'].mean():.2f}")
        st.metric("Output A", f"{total_a:.0f} TON")
        
    with cb:
        st.markdown("#### 🅱️ LINE B")
        c_3, c_4 = st.columns(2)
        c_3.metric("Moisture", f"{df_angka['Finish Moist B'].mean():.2f}%")
        c_4.metric("Particle", f"{df_angka['Finish Particle B'].mean():.2f}")
        st.metric("Output B", f"{total_b:.0f} TON")

    with st.expander("🔍 Lihat Data Mentah"):
        st.dataframe(df)

except Exception as e:
    st.error(f"Terjadi Kesalahan: {e}")
