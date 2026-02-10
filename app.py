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
    # Default saya ubah ke index 0 (Tanggal 1) untuk mengetes fitur keamanan
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=0) 
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ==========================================
# 2. PROSES DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW (MODE SUPER TEXT)
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)

    # ==========================================
    # 🚨 SECURITY CHECK: VALIDASI TANGGAL 🚨
    # ==========================================
    # Kita cek Cell A2 (Baris 1, Kolom 0) atau sekitarnya dimana tanggal ditulis.
    # Format di Excel biasanya: "Date : 6-Jan"
    
    valid_data = False
    tanggal_excel = "-"
    
    try:
        # Ambil teks di pojok kiri atas (biasanya baris ke-2 atau ke-3)
        header_area = df_raw.iloc[0:4, 0].astype(str).values.flatten()
        for h in header_area:
            if "date" in h.lower() or "tanggal" in h.lower() or "-" in h:
                tanggal_excel = h
                # Cek apakah angka tanggal yang dipilih user ada di teks tersebut?
                # Contoh: User pilih "6". Excel "6-Jan". -> COCOK.
                # Contoh: User pilih "1". Excel "6-Jan". -> TIDAK COCOK.
                
                # Regex mencari angka tanggal di excel (misal '6' dari '6-Jan')
                match = re.search(r'\b' + re.escape(pilihan_sheet) + r'\b', h)
                if match:
                    valid_data = True
                    break
    except:
        pass

    # JIKA TANGGAL TIDAK COCOK / SHEET TIDAK ADA -> STOP PROGRAM
    if not valid_data:
        st.error(f"⚠️ **DATA KOSONG / SHEET TIDAK DITEMUKAN**")
        st.warning(f"Anda memilih Tanggal **{pilihan_sheet}**, tetapi sistem membaca file ini adalah data Tanggal: **{tanggal_excel}**.")
        st.info("Kemungkinan Sheet untuk tanggal yang Anda pilih belum dibuat di Excel. Google secara otomatis mengirimkan sheet default.")
        st.stop() # BERHENTI DISINI, JANGAN TAMPILKAN DATA NGAWUR

    # ==========================================
    # B. SMART SEARCH (LOGIKA ANTI-HEADER) 🏆
    # ==========================================
    produk_a = "-"
    produk_b = "-"
    idx_start = 6 

    try:
        # 1. Cari baris "9:00"
        scan_area = df_raw.iloc[:25, 0].astype(str)
        matches = scan_area[scan_area.str.contains(r"9[:\.]00", regex=True)].index
        
        if not matches.empty:
            idx_center = matches[0]
            idx_start = idx_center 
            
            # DAFTAR BLACKLIST DIPERKETAT
            # Tambahkan "max", "min" agar "15 max" tidak terambil
            blacklist = ["nan", "none", "-", "", "moisture", "particle", "mesh", "null", 
                         "time", "tonnage", "paraph", "checker", "ok", "no", "shift", 
                         "max", "min", "avg", "phadla", "reza", "qc", "admin", "spv", "juan"]
            
            # FUNGSI PEMILIH CERDAS
            def get_best_candidate(row_indices, col_start, col_end):
                candidates = []
                
                for r in row_indices:
                    if r < 0 or r >= len(df_raw): continue
                    vals = df_raw.iloc[r, col_start:col_end].values.flatten()
                    for v in vals:
                        v_clean = str(v).strip()
                        v_lower = v_clean.lower()
                        
                        # Filter Panjang & Blacklist
                        if len(v_clean) > 1:
                            is_blacklist = False
                            for bad_word in blacklist:
                                if bad_word in v_lower:
                                    is_blacklist = True
                                    break
                            
                            if not is_blacklist:
                                # Harus ada huruf (menghindari angka murni)
                                if re.search('[a-zA-Z]', v_clean):
                                    candidates.append(v_clean)
                
                if not candidates:
                    return "-"
                
                # --- PRIORITAS SELEKSI ---
                
                # 1. Prioritas TERTINGGI: Mengandung ANGKA + HURUF (Cth: Z 125, Z 211)
                # "15 max" sudah kena blacklist, jadi aman.
                for c in candidates:
                    if re.search(r'\d', c) and re.search(r'[a-zA-Z]', c): 
                        return c
                
                # 2. Prioritas KEDUA: Huruf Besar Semua (Cth: PRODUCT HOLD BLEND)
                # Nama orang biasanya "Juan", "Phadla" (Huruf besar kecil)
                for c in candidates:
                    if c.isupper() and len(c) > 3:
                        return c

                # 3. Prioritas KETIGA: Kata Kunci Khusus
                for c in candidates:
                    if "PRODUCT" in c.upper() or "HOLD" in c.upper() or "SMBE" in c.upper():
                        return c

                return candidates[0]

            rows_to_scan = [idx_center, idx_center-1, idx_center+1]
            
            # SCAN LINE A
            res_a = get_best_candidate(rows_to_scan, 6, 11)
            if res_a != "-": produk_a = res_a

            # SCAN LINE B
            res_b = get_best_candidate(rows_to_scan, 11, 18)
            if res_b != "-": produk_b = res_b
            
    except Exception as e:
        pass

    # ==========================================
    # C. OLAH DATA TABEL
    # ==========================================
    
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
    
    df = df.iloc[:, :len(nama_kolom)]
    if len(df.columns) < len(nama_kolom):
        for i in range(len(nama_kolom) - len(df.columns)):
            df[f"Col_{i}"] = np.nan
    df.columns = nama_kolom[:len(df.columns)]
    
    # D. BERSIHKAN ANGKA
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
            data_valid = series_data[~series_data.isin(["-", "", "nan", "None", " "])].dropna()
            if not data_valid.empty:
                last_val = str(data_valid.iloc[-1])
                if "-" in last_val:
                    parts = last_val.split("-")
                    if parts[-1].strip().replace('.','').isdigit():
                         total = float(parts[-1])
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
        
        st.markdown("### 🏷️ Informasi Batch Produksi")
        col_info_1, col_info_2 = st.columns(2)
        
        st.markdown("""
        <style>
        .box-info { 
            padding: 20px; border-radius: 12px; color: white; text-align: center; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
        }
        .biru { background: linear-gradient(135deg, #3498db, #2980b9); }
        .merah { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .judul { font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; }
        .isi { font-size: 26px; font-weight: 800; margin-top: 5px; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1:
            txt_a = produk_a if produk_a not in ["-", ""] else "(Belum Diisi)"
            st.markdown(f"""
            <div class="box-info biru">
                <div class="judul">JENIS PRODUK A (KIRI)</div>
                <div class="isi">{txt_a}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_info_2:
            txt_b = produk_b if produk_b not in ["-", ""] else "(Kosong)"
            st.markdown(f"""
            <div class="box-info merah">
                <div class="judul">JENIS PRODUK B (KANAN)</div>
                <div class="isi">{txt_b}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()

        # --- ROTARY & FINISH ---
        st.subheader("🔥 Rotary Process (Gabungan A & B)")
        
        gabungan_rm = pd.concat([df_angka["RM Rotary Moist A"], df_angka["RM Rotary Moist B"]])
        gabungan_rot = pd.concat([df_angka["Rotary Moist A"], df_angka["Rotary Moist B"]])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{gabungan_rm.mean():.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{gabungan_rot.mean():.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B")
        
        st.markdown("---")

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
    st.error("Sedang memuat data...")
