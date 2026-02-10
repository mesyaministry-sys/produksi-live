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
    # Default pilih tanggal 10 agar langsung terlihat hasilnya
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW (BACA SEMUA SEBAGAI TEKS BIAR AMAN)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ==========================================
    # 🚨 SECURITY CHECK: TANGGAL WAJIB SAMA 🚨
    # ==========================================
    tanggal_excel = None
    tanggal_valid = False

    # Cari tulisan "Date" di 5 baris pertama
    try:
        header_area = df_raw.iloc[:6, 0].values.flatten()
        for cell in header_area:
            txt = str(cell).lower()
            if "date" in txt or "tanggal" in txt:
                # Ambil angka pertama yang muncul di baris itu
                # Contoh: "Date : 10 - Jan" -> ketemu "10"
                angka_di_excel = re.findall(r'\d+', txt)
                if angka_di_excel:
                    tanggal_excel = angka_di_excel[0]
                    
                    # Bandingkan: Pilihan User (1) vs Excel (10) ?
                    if int(tanggal_excel) == int(pilihan_sheet):
                        tanggal_valid = True
                    break
    except:
        pass

    # HAKIM: JIKA TANGGAL BEDA -> STOP PROGRAM!
    # Ini mengatasi masalah Sheet 1 kosong tapi muncul data Sheet 6
    if tanggal_excel and not tanggal_valid:
        st.error(f"⛔ DATA TIDAK COCOK / SHEET KOSONG")
        st.warning(f"Anda memilih Tanggal **{pilihan_sheet}**, tapi sistem menerima data Tanggal **{tanggal_excel}**.")
        st.info("Penyebab: Sheet untuk tanggal yang Anda pilih belum dibuat di Excel, sehingga Google mengirimkan sheet lain secara acak.")
        st.stop() # 🛑 BERHENTI DISINI. JANGAN TAMPILKAN APAPUN.

    # ==========================================
    # B. PENCARIAN PRODUK (LOGIKA SARINGAN KETAT)
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 

    # Daftar Kata Terlarang (Termasuk Nama Orang & Satuan)
    blacklist = ["nan", "none", "-", "", "moisture", "particle", "mesh", "null", 
                 "time", "tonnage", "paraph", "checker", "ok", "no", "shift", 
                 "max", "min", "avg", "%", 
                 "phadla", "reza", "qc", "admin", "juan", "dian", "adi"]

    def is_valid_product(text):
        t = text.strip()
        t_lower = t.lower()
        
        # 1. Cek Panjang & Blacklist
        if len(t) < 2: return False
        for bad in blacklist:
            if bad in t_lower: return False
            
        # 2. Cek Apakah Ini Angka Murni? (Misal: "11,36" atau "15")
        # Kita ganti koma jadi titik, lalu cek apakah dia angka
        cek_angka = t.replace(',', '.').replace('.', '')
        if cek_angka.isdigit(): return False # Kalo angka, TOLAK.

        # 3. Cek Format Nama Orang (Title Case: "Juan", "Phadla")
        # Produk biasanya UPPERCASE (PRODUCT HOLD) atau Ada Angka (Z 125)
        # Jika Huruf Besar Awal doang + Gak ada angka = Nama Orang -> TOLAK
        if t[0].isupper() and t[1:].islower() and not re.search(r'\d', t):
            return False

        # 4. HARUS ADA HURUF (A-Z)
        if not re.search(r'[a-zA-Z]', t): return False

        return True

    try:
        # Cari Baris Jam 9:00
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_start = matches[0]
            
            # --- CARI LINE A (KIRI) ---
            # Scan Kolom 6 sampai 10 (G, H, I, J)
            candidates_a = []
            # Scan 3 baris (atas, tengah, bawah)
            for r in [idx_start, idx_start-1, idx_start+1]: 
                vals = df_raw.iloc[r, 6:11].values.flatten()
                for v in vals:
                    v_str = str(v)
                    if is_valid_product(v_str):
                        candidates_a.append(v_str)
            
            # Prioritas: Ambil yang ada angkanya dulu (Z 125)
            for c in candidates_a:
                if re.search(r'\d', c): 
                    produk_a = c; break
            if produk_a == "-" and candidates_a: produk_a = candidates_a[0]

            # --- CARI LINE B (KANAN) ---
            # Scan Kolom 11 sampai 16 (L, M, N, O, P)
            candidates_b = []
            for r in [idx_start, idx_start-1, idx_start+1]:
                vals = df_raw.iloc[r, 11:17].values.flatten()
                for v in vals:
                    v_str = str(v)
                    if is_valid_product(v_str):
                        candidates_b.append(v_str)
            
            # Prioritas: Cari kata PRODUCT / HOLD
            for c in candidates_b:
                if "PRODUCT" in c.upper() or "HOLD" in c.upper():
                    produk_b = c; break
            if produk_b == "-" and candidates_b: produk_b = candidates_b[0]

    except:
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
    
    # Potong kolom sesuai panjang
    df = df.iloc[:, :len(nama_kolom)]
    if len(df.columns) < len(nama_kolom):
        for i in range(len(nama_kolom) - len(df.columns)):
            df[f"Col_{i}"] = np.nan
    df.columns = nama_kolom[:len(df.columns)]
    
    # Bersihkan Angka
    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B"]
    
    df_angka = df.copy()
    for col in cols_angka:
        if col in df_angka.columns:
            df_angka[col] = df_angka[col].astype(str).str.replace(',', '.', regex=False)
            df_angka[col] = pd.to_numeric(df_angka[col], errors='coerce')

    # Hitung Tonnage
    def hitung_tonnage(series):
        try:
            valid = series[~series.isin(["-", "", "nan", "None"])].dropna()
            if not valid.empty:
                val = str(valid.iloc[-1])
                if "-" in val: return float(val.split("-")[-1])
                if val.replace('.','').isdigit(): return float(val)
        except: pass
        return 0

    ton_a = hitung_tonnage(df["Tonnage A"])
    ton_b = hitung_tonnage(df["Tonnage B"])
    
    # ==========================================
    # D. TAMPILAN DASHBOARD
    # ==========================================
    if not df.empty:
        st.success(f"✅ Data Tanggal {pilihan_sheet} Valid & Terbaca!")
        
        # INFO PRODUK
        st.markdown("### 🏷️ Informasi Batch Produksi")
        c1, c2 = st.columns(2)
        
        st.markdown("""
        <style>
        .box { padding: 15px; border-radius: 8px; color: white; text-align: center; margin-bottom: 10px; }
        .blue { background: #3498db; } .red { background: #e74c3c; }
        .t { font-size: 14px; font-weight: bold; opacity: 0.9; }
        .v { font-size: 24px; font-weight: 800; }
        </style>
        """, unsafe_allow_html=True)

        txt_a = produk_a if produk_a not in ["-", ""] else "(Belum Diisi)"
        txt_b = produk_b if produk_b not in ["-", ""] else "(Kosong)"

        with c1:
            st.markdown(f'<div class="box blue"><div class="t">LINE A (KIRI)</div><div class="v">{txt_a}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="box red"><div class="t">LINE B (KANAN)</div><div class="v">{txt_b}</div></div>', unsafe_allow_html=True)

        st.divider()

        # METRIK ROTARY
        st.subheader("🔥 Rotary Process")
        gab_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gab_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist", f"{gab_rm.mean():.2f}%")
        m2.metric("Rotary Moist", f"{gab_rot.mean():.2f}%")
        m3.metric("Total Output", f"{ton_a + ton_b:.0f} TON")
        
        st.markdown("---")

        # METRIK FINISH
        ca, cb = st.columns(2)
        with ca:
            st.markdown("#### 🅰️ LINE A")
            if df_angka['Finish Moist A'].isnull().all(): st.info("Menunggu data...")
            else:
                c1, c2 = st.columns(2)
                c1.metric("Moisture", f"{df_angka['Finish Moist A'].mean():.2f}%")
                c2.metric("Particle", f"{df_angka['Finish Particle A'].mean():.2f}")
                st.metric("Prod. Line A", f"{ton_a:.0f} TON")

        with cb:
            st.markdown("#### 🅱️ LINE B")
            if df_angka['Finish Moist B'].isnull().all(): st.info("Tidak ada produksi.")
            else:
                c3, c4 = st.columns(2)
                c3.metric("Moisture", f"{df_angka['Finish Moist B'].mean():.2f}%")
                c4.metric("Particle", f"{df_angka['Finish Particle B'].mean():.2f}")
                st.metric("Prod. Line B", f"{ton_b:.0f} TON")

        with st.expander("🔍 Data Mentah"):
            st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("Sedang memuat data...")
