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
st.caption("Created : Mahesya | Mode: Toleransi Tinggi")

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
    # BACA DATA (Anti Error)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # --- 🚨 CEK TANGGAL (VERSI LEMBUT / TIDAK MEMBLOKIR) 🚨 ---
    info_tanggal = "Tidak Terdeteksi"
    try:
        header_area = df_raw.iloc[:8, :8].values.flatten()
        for cell in header_area:
            txt = str(cell).lower()
            if "date" in txt or "tanggal" in txt:
                angka = re.findall(r'\d+', txt)
                if angka:
                    info_tanggal = angka[0]
                    break
    except:
        pass
    
    # HANYA PERINGATAN KUNING (TIDAK STOP PROGRAM)
    if info_tanggal != "Tidak Terdeteksi" and info_tanggal != pilihan_sheet:
        st.warning(f"⚠️ **Peringatan:** Anda memilih Tanggal {pilihan_sheet}, tapi file Excel terlihat seperti Tanggal {info_tanggal}. (Data tetap ditampilkan di bawah)")
    elif info_tanggal == "Tidak Terdeteksi":
        st.caption("ℹ️ Info: Verifikasi tanggal otomatis tidak berjalan (Format Header Excel mungkin berbeda), menampilkan data apa adanya.")

    # ==========================================
    # 3. PENCARIAN PRODUK (LOGIKA CARI DI SEKITAR)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 

    # Filter Kata Sampah
    blacklist = ["nan", "none", "-", "", "moisture", "particle", "checker", "ok", "no", 
                 "max", "min", "avg", "%", "phadla", "reza", "qc", "juan"]

    def saring_produk(text):
        t = text.strip()
        # 1. Tolak jika pendek/sampah
        if len(t) < 2: return False
        if any(b in t.lower() for b in blacklist): return False
        
        # 2. Tolak Angka Murni (11.36)
        clean_num = t.replace('.', '').replace(',', '')
        if clean_num.isdigit(): return False
        
        # 3. Tolak Nama Orang (Huruf Besar Awal, sisanya kecil, tanpa angka)
        # Contoh: "Juan" -> Ditolak. "Z 125" -> Diterima. "PRODUCT" -> Diterima.
        has_digit = bool(re.search(r'\d', t))
        if t[0].isupper() and not t.isupper() and not has_digit:
            return False
            
        # 4. Terima jika: Huruf Besar Semua ATAU Ada Angkanya
        if t.isupper() or has_digit:
            return True
            
        return False

    try:
        # Cari Baris 9:00
        scan_col = df_raw.iloc[:30, 0].astype(str)
        matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0]
            
            # SCAN LINE A (Cek kolom G, H, I, J / Index 6-10)
            # Kita cek 3 baris: Baris jam 9, baris atasnya, baris bawahnya
            kandidat_a = []
            for r in [idx_start, idx_start-1, idx_start+1]:
                vals = df_raw.iloc[r, 6:11].values.flatten()
                for v in vals:
                    if saring_produk(str(v)):
                        kandidat_a.append(str(v))
            
            # Prioritas: Ambil yang ada angkanya (Z 125)
            for k in kandidat_a:
                if re.search(r'\d', k): produk_a = k; break
            if produk_a == "-" and kandidat_a: produk_a = kandidat_a[0]

            # SCAN LINE B (Cek kolom L, M, N, O / Index 11-16)
            kandidat_b = []
            for r in [idx_start, idx_start-1, idx_start+1]:
                vals = df_raw.iloc[r, 11:17].values.flatten()
                for v in vals:
                    if saring_produk(str(v)):
                        kandidat_b.append(str(v))
            
            if kandidat_b: produk_b = kandidat_b[0]
            
    except:
        pass

    # ==========================================
    # 4. TAMPILAN
    # ==========================================
    
    # Ambil Data Angka
    df = df_raw.iloc[idx_start:].copy() 
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
    cols_num = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    df_angka = df.copy()
    for c in cols_num:
        if c in df_angka.columns:
            df_angka[c] = df_angka[c].astype(str).str.replace(',', '.', regex=False)
            df_angka[c] = pd.to_numeric(df_angka[c], errors='coerce')

    def get_ton(s):
        try:
            v = s[~s.isin(["-", "", "nan"])].dropna()
            if not v.empty:
                val = str(v.iloc[-1])
                if "-" in val: return float(val.split("-")[-1])
                return float(val)
        except: return 0
        return 0

    ton_a = get_ton(df["Tonnage A"])
    ton_b = get_ton(df["Tonnage B"])

    # UI
    if not df.empty:
        st.success(f"✅ Data Tanggal {pilihan_sheet} Ditampilkan")
        
        st.markdown("### 🏷️ Informasi Batch Produksi")
        c1, c2 = st.columns(2)
        
        val_a = produk_a if produk_a != "-" else "(Belum Terbaca)"
        val_b = produk_b if produk_b != "-" else "(Kosong)"
        
        st.markdown("""
        <style>
        .card { padding: 20px; border-radius: 10px; color: white; text-align: center; }
        .bg-blue { background-color: #2980b9; }
        .bg-red { background-color: #c0392b; }
        .head { font-size: 14px; font-weight: bold; opacity: 0.8; margin-bottom: 5px; }
        .main { font-size: 24px; font-weight: 800; }
        </style>
        """, unsafe_allow_html=True)
        
        with c1:
            st.markdown(f'<div class="card bg-blue"><div class="head">LINE A (KIRI)</div><div class="main">{val_a}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="card bg-red"><div class="head">LINE B (KANAN)</div><div class="main">{val_b}</div></div>', unsafe_allow_html=True)
            
        st.divider()
        
        # Metrik
        st.subheader("🔥 Rotary Process")
        gab_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gab_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
        
        k1, k2, k3 = st.columns(3)
        k1.metric("RM Rotary Avg", f"{gab_rm.mean():.2f}%")
        k2.metric("Rotary Avg", f"{gab_rot.mean():.2f}%")
        k3.metric("Total Output", f"{ton_a + ton_b:.0f} TON")
        
        st.markdown("---")
        
        ca, cb = st.columns(2)
        with ca:
            st.markdown("#### 🅰️ LINE A")
            c1, c2 = st.columns(2)
            c1.metric("Moisture", f"{df_angka['Finish Moist A'].mean():.2f}%")
            c2.metric("Particle", f"{df_angka['Finish Particle A'].mean():.2f}")
            st.metric("Output A", f"{ton_a:.0f} TON")
            
        with cb:
            st.markdown("#### 🅱️ LINE B")
            c3, c4 = st.columns(2)
            c3.metric("Moisture", f"{df_angka['Finish Moist B'].mean():.2f}%")
            c4.metric("Particle", f"{df_angka['Finish Particle B'].mean():.2f}")
            st.metric("Output B", f"{ton_b:.0f} TON")
            
        with st.expander("🔍 Lihat Data Mentah"):
            st.dataframe(df)
            
    else:
        st.error("Data kosong atau sheet tidak ditemukan.")

except Exception as e:
    st.error(f"Terjadi kesalahan teknis: {e}")
