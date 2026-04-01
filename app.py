import streamlit as st
import pandas as pd
import numpy as np
import re
import time
import plotly.graph_objects as go # <-- Library untuk grafik elegan dan presisi

# ==========================================
# ⚙️ KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(page_title="Monitoring Produksi", layout="wide", page_icon="🏭")

# ==========================================
# 🚫 SEMBUNYIKAN ELEMEN STREAMLIT (MENU, GITHUB, FOOTER)
# Dipindah ke atas agar berlaku di halaman Login juga
# ==========================================
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            [data-testid="stHeader"] {visibility: hidden !important;}
            [data-testid="stToolbar"] {visibility: hidden !important;}
            [data-testid="stDecoration"] {visibility: hidden !important;}
            .stDeployButton {display: none !important;}
            .reportview-container .main .block-container {padding-top: 1rem;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 🔒 SISTEM LOGIN (KEAMANAN)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # Tampilan Halaman Login
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔒 PROTECTED ACCESS")
        st.caption("Silakan login untuk mengakses Dashboard Monitoring Produksi.")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("LOGIN MASUK"):
            if username == "mahesya13" and password == "swasa226":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("Username atau Password Salah!")
    
    # Hentikan script di sini jika belum login
    st.stop()

# ==========================================
# ⚙️ KONFIGURASI DATABASE BULANAN
# ==========================================
DAFTAR_FILE = {
    "Januari 2026": "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY",  
    "Februari 2026": "1Gy7h6ZUw2i-JoNFZLN7t7M8Ir1bsN2mLyfizK4zjnDA",              
    "Maret 2026": "17I_fQ7mEB7L4ovYJ1IKFsIe-FkcSBmk-v-l5mD7xU7Y",
    "April 2026": "",
}

# ==========================================
# 🎨 TAMPILAN HEADER DENGAN LOGO
# ==========================================
# Layout Header: Logo di Kiri, Judul di Kanan
col_logo, col_judul = st.columns([1, 6])

with col_logo:
    # Menampilkan Logo (Pastikan file ada di folder github)
    try:
        st.image("logo_swasa.png.png", width=140)
    except:
        st.warning("Logo not found")

with col_judul:
    st.title("MONITORING PRODUKSI BE")
    st.caption("Dev : Mahesya | 2026 🚦") 

st.divider()

# ==========================================
# 1. MENU SAMPING (SIDEBAR)
# ==========================================
# Opsi variasi 28A, dll dihapus agar akurat 1-31
daftar_tanggal = [str(i) for i in range(1, 32)]

with st.sidebar:
    st.header("🗂️ Menu Utama")
    pilihan_bulan = st.selectbox("Pilih Bulan Laporan:", list(DAFTAR_FILE.keys()))
    SHEET_ID_AKTIF = DAFTAR_FILE[pilihan_bulan]
    
    st.divider()
    st.subheader("📅 Periode Harian")
    pilihan_sheet = st.selectbox("Pilih Tanggal (Sheet):", daftar_tanggal, index=9) 
    
    # FITUR AUTO REFRESH
    auto_refresh = st.checkbox("🔄 Auto Refresh (60s)", value=False)
    
    if st.button("🔄 Refresh Manual"):
        st.cache_data.clear()
        st.rerun()
    
    # Tombol Logout
    st.markdown("---")
    if st.button("🔒 LOGOUT"):
        st.session_state['logged_in'] = False
        st.rerun()

    if auto_refresh:
        time.sleep(60) # Tunggu 60 detik
        st.cache_data.clear()
        st.rerun()

# ==========================================
# 2. PROSES DATA
# ==========================================
if "MASUKKAN_ID" in SHEET_ID_AKTIF or SHEET_ID_AKTIF == "":
    st.info(f"📁 Laporan untuk bulan **{pilihan_bulan}** belum dihubungkan/tersedia.")
    st.stop()

url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_AKTIF}/gviz/tq?tqx=out:csv&sheet={pilihan_sheet}'

try:
    # A. BACA DATA RAW
    try:
        df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False, on_bad_lines='skip')
    except Exception:
        st.warning(f"⚠️ Data belum terinput untuk Tanggal {pilihan_sheet} (Sheet tidak ditemukan).")
        st.stop()

    # ==========================================
    # B. CARI JANGKAR (JAM 9:00)
    # ==========================================
    idx_900 = 6 
    found_anchor = False

    # Cek apakah dataframe kosong
    if df_raw.empty:
        st.warning(f"⚠️ Data belum terinput untuk Tanggal {pilihan_sheet}.")
        st.stop()

    scan_col = df_raw.iloc[:30, 0].astype(str)
    matches = scan_col[scan_col.str.contains(r"9[:\.]00", regex=True)].index
    
    if not matches.empty:
        idx_900 = matches[0]
        found_anchor = True
    else:
        st.warning(f"⚠️ Data belum terinput untuk Tanggal {pilihan_sheet} (Data Jam 09:00 belum masuk).")
        st.stop()

    # ==========================================
    # C. CARI PRODUK & FORMULA (DATA RAW PROCESSING)
    # ==========================================
    produk_a, produk_b, produk_c = "-", "-", "-"
    f_bbku, f_bakar, f_loading, f_remark = "-", "-", "-", "-" 

    def valid_prod(val):
        t = str(val).strip()
        if len(t) < 2: return False
        if t.replace('.','').replace(',','').isdigit(): return False 
        if re.match(r'^\d+-\d+$', t): return False
        if any(x in t.lower() for x in ["moisture", "particle", "mesh", "max", "min", "tonnage", "time"]): return False
        return True

    # Produk A
    for r in range(idx_900, max(0, idx_900-4), -1):
        for c in [8, 9, 10]:
            if df_raw.shape[1] > c:
                val = df_raw.iloc[r, c]
                if valid_prod(val):
                    if any(char.isdigit() for char in str(val)):
                        produk_a = str(val).strip(); break
        if produk_a != "-": break

    # Produk B
    for r in range(idx_900, max(0, idx_900-4), -1):
        for c in [13, 14, 15]:
            if df_raw.shape[1] > c:
                val = df_raw.iloc[r, c]
                if valid_prod(val):
                    if str(val).isupper():
                        produk_b = str(val).strip(); break
        if produk_b != "-": break

    # Produk C
    for r in range(idx_900, max(0, idx_900-4), -1):
        for c in [18, 19, 20]:
            if df_raw.shape[1] > c:
                val = df_raw.iloc[r, c]
                if valid_prod(val):
                    if str(val).isupper() or any(char.isdigit() for char in str(val)):
                        produk_c = str(val).strip(); break
        if produk_c != "-": break

    if produk_a == "-": produk_a = "(Belum Diisi)"
    if produk_b == "-": produk_b = "(Kosong)"
    if produk_c == "-": produk_c = "(Kosong)"

    # Formula & Remark
    for i in range(25, min(60, len(df_raw))):
        row_txt = " ".join(df_raw.iloc[i].astype(str).values).upper().replace("_", " ").replace("  ", " ")
        if "BBKU" in row_txt and ":" in row_txt: f_bbku = row_txt.split(":")[-1].split("FORMULA")[0].strip()
        if "BAHAN BAKAR" in row_txt and ":" in row_txt: f_bakar = row_txt.split(":")[-1].split("LOADING")[0].strip()
        if "LOADING" in row_txt and ":" in row_txt: f_loading = row_txt.split(":")[-1].strip()
        
        # Mencari Catatan/Remark
        for j in range(df_raw.shape[1]):
            cell_val = str(df_raw.iloc[i, j]).strip().upper()
            if "CATATAN" in cell_val:
                if i + 1 < len(df_raw):
                    val_below = str(df_raw.iloc[i+1, j]).strip()
                    if val_below and val_below.upper() not in ["NAN", "NONE"]:
                        f_remark = val_below
                break

    for x in [f_bbku, f_bakar, f_loading]: x = x.replace("NAN", "").replace(",", "").strip()
    if len(f_bbku)<2: f_bbku="-" 
    if len(f_bakar)<2: f_bakar="-" 
    if len(f_loading)<2: f_loading="-"
    if len(f_remark)<2: f_remark="-" 

    # ==========================================
    # D. DATA ANGKA
    # ==========================================
    idx_data_start = idx_900
    if "8" in str(df_raw.iloc[idx_900-1, 0]): idx_data_start = idx_900 - 1
        
    df = df_raw.iloc[idx_data_start:].copy()
    df_clean = pd.DataFrame()
    
    try:
        df_clean["Jam"]               = df.iloc[:, 0] 
        df_clean["RM Rotary Moist A"] = df.iloc[:, 1]
        df_clean["Rotary Moist A"]    = df.iloc[:, 2]
        
        df_clean["Jam Rotary B"]      = df.iloc[:, 3] if df.shape[1] > 3 else np.nan
        df_clean["RM Rotary Moist B"] = df.iloc[:, 4]
        df_clean["Rotary Moist B"]    = df.iloc[:, 5]
        
        # Pembacaan Jam Finish Product & Paraph Checker
        df_clean["Jam Finish A"]      = df.iloc[:, 6] if df.shape[1] > 6 else np.nan
        df_clean["Finish Moist A"]    = df.iloc[:, 7]
        df_clean["Finish Particle A"] = df.iloc[:, 8]
        df_clean["Tonnage A"]         = df.iloc[:, 9]
        df_clean["Checker A"]         = df.iloc[:, 10] if df.shape[1] > 10 else np.nan
        
        df_clean["Jam Finish B"]      = df.iloc[:, 11] if df.shape[1] > 11 else np.nan
        df_clean["Finish Moist B"]    = df.iloc[:, 12]
        df_clean["Finish Particle B"] = df.iloc[:, 13]
        df_clean["Tonnage B"]         = df.iloc[:, 14]
        df_clean["Checker B"]         = df.iloc[:, 15] if df.shape[1] > 15 else np.nan

        # Tambahan Kolom C & Remarks (PENYESUAIAN DI SINI)
        if df.shape[1] > 19:
            df_clean["Jam Finish C"]      = df.iloc[:, 16] if df.shape[1] > 16 else np.nan
            df_clean["Finish Moist C"]    = df.iloc[:, 17]
            df_clean["Finish Particle C"] = df.iloc[:, 18]
            df_clean["Tonnage C"]         = df.iloc[:, 19]
            df_clean["Checker C"]         = df.iloc[:, 20] if df.shape[1] > 20 else np.nan
            
            # Sapu bersih semua kolom dari indeks 21 sampai habis untuk area Remarks
            if df.shape[1] > 21:
                # Ambil semua data sisa, jadikan string, abaikan NaN
                remarks_df = df.iloc[:, 21:].fillna("").astype(str)
                # Gabungkan per baris: jika ada data di kolom 21, 22, 23 dst, satukan dengan spasi
                df_clean["Remarks"] = remarks_df.apply(
                    lambda row: " ".join([val.strip() for val in row if val.strip() and val.strip().lower() not in ['nan', 'none']]), 
                    axis=1
                )
                # Rapikan yang kosong kembali menjadi NaN
                df_clean["Remarks"] = df_clean["Remarks"].replace("", np.nan)
            else:
                df_clean["Remarks"] = np.nan
        else:
            df_clean["Jam Finish C"]      = np.nan
            df_clean["Finish Moist C"]    = np.nan
            df_clean["Finish Particle C"] = np.nan
            df_clean["Tonnage C"]         = np.nan
            df_clean["Checker C"]         = np.nan
            df_clean["Remarks"]           = np.nan

    except IndexError:
        st.warning("⚠️ Data belum terinput lengkap (Kolom Excel belum sesuai). Pastikan Sheet memiliki kolom produk C.")
        st.stop()

    # Cleaning Angka
    cols_angka = ["RM Rotary Moist A", "Rotary Moist A", "RM Rotary Moist B", "Rotary Moist B", 
                  "Finish Moist A", "Finish Particle A", "Finish Moist B", "Finish Particle B",
                  "Finish Moist C", "Finish Particle C"]
    
    for c in cols_angka:
        df_clean[c] = df_clean[c].astype(str).str.replace(',', '.', regex=False)
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    # Hitung Tonnage
    def hitung_tonnage(series):
        total = 0
        try:
            valid = series[~series.astype(str).isin(["-", "", "nan", "None"])].dropna()
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
    total_ton_c = hitung_tonnage(df_clean["Tonnage C"]) 
    total_gabungan = total_ton_a + total_ton_b + total_ton_c

    # ==========================================
    # E. TAMPILAN DASHBOARD
    # ==========================================
    if not df_clean.empty:
        st.success(f"✅ Laporan: **{pilihan_bulan}** | Tanggal: **{pilihan_sheet}**")
        
        # --- INFO KARTU PRODUK ---
        col_info_1, col_info_2, col_info_3 = st.columns(3)
        st.markdown("""
        <style>
        .card { padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .bg-blue { background: linear-gradient(135deg, #3498db, #2980b9); }
        .bg-red { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .bg-green { background: linear-gradient(135deg, #2ecc71, #27ae60); }
        .bg-dark { background-color: #2c3e50; border: 1px solid #34495e; padding: 15px; border-radius: 8px; }
        .label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; margin-bottom: 5px; color: #ecf0f1; }
        .value { font-size: 24px; font-weight: 800; }
        .value-small { font-size: 18px; font-weight: bold; color: #f1c40f; }
        </style>
        """, unsafe_allow_html=True)

        with col_info_1: st.markdown(f'<div class="card bg-blue"><div class="label">JENIS PRODUK A (KIRI)</div><div class="value">{produk_a}</div></div>', unsafe_allow_html=True)
        with col_info_2: st.markdown(f'<div class="card bg-red"><div class="label">JENIS PRODUK B (TENGAH)</div><div class="value">{produk_b}</div></div>', unsafe_allow_html=True)
        with col_info_3: st.markdown(f'<div class="card bg-green"><div class="label">JENIS PRODUK C (KANAN)</div><div class="value">{produk_c}</div></div>', unsafe_allow_html=True)
        
        # --- REMARK ---
        c1, c2, c3, c4 = st.columns(4) 
        with c1: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">FORMULA BBKU</div><div class="value-small">{f_bbku}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">BAHAN BAKAR</div><div class="value-small">{f_bakar}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">LOADING</div><div class="value-small">{f_loading}</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="bg-dark" style="text-align:center;"><div class="label">REMARK</div><div class="value-small">{f_remark}</div></div>', unsafe_allow_html=True)

        st.divider()
        
        # --- METRIK ---
        rm_a = df_clean[df_clean["RM Rotary Moist A"] > 0]["RM Rotary Moist A"]
        rm_b = df_clean[df_clean["RM Rotary Moist B"] > 0]["RM Rotary Moist B"]
        avg_rm = pd.concat([rm_a, rm_b]).mean()
        
        rot_a = df_clean[df_clean["Rotary Moist A"] > 0]["Rotary Moist A"]
        rot_b = df_clean[df_clean["Rotary Moist B"] > 0]["Rotary Moist B"]
        avg_rot = pd.concat([rot_a, rot_b]).mean()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("RM Rotary Moist (Avg)", f"{avg_rm:.2f}%", "40 Max")
        m2.metric("Rotary Moist (Avg)", f"{avg_rot:.2f}%", "12-15")
        m3.metric("Total Output Harian", f"{total_gabungan:.0f} TON", "A + B + C")
        
        st.markdown("---")

        # --- DETAIL LINE (Disesuaikan jadi 3 kolom) ---
        ca, cb, cc = st.columns(3)
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

        with cc:
            st.markdown(f"#### 🅲 LINE C")
            c5, c6 = st.columns(2)
            c5.metric("Moisture C", f"{df_clean['Finish Moist C'].mean():.2f}%")
            c6.metric("Particle C", f"{df_clean['Finish Particle C'].mean():.2f}")
            st.metric("Produksi Line C", f"{total_ton_c:.0f} TON")

        # ==========================================
        # 📈 GRAFIK TREN HARIAN (AKURAT & ELEGAN MENGGUNAKAN PLOTLY)
        # ==========================================
        st.markdown("---")
        st.subheader("📈 Grafik Tren Harian")
        chart_data = df_clean.copy()

        # Fungsi pintar untuk memproses string waktu agar presisi dan mengenali pergantian hari (midnight)
        def parse_time_sequence(series):
            s = series.astype(str).str.strip()
            dt_list = []
            base_date = pd.to_datetime('2000-01-01')
            last_hour = None
            
            for val in s:
                if val in ['', 'nan', 'None', 'NaN']:
                    dt_list.append(pd.NaT)
                    continue
                    
                match = re.search(r'(\d{1,2})[:\.](\d{2})', val)
                if match:
                    h, m = int(match.group(1)), int(match.group(2))
                    
                    # Jika jam anjlok drastis (contoh 23:00 ke 01:00), berarti sudah ganti hari
                    if last_hour is not None and h < last_hour - 4:
                        base_date += pd.Timedelta(days=1)
                    
                    try:
                        dt = pd.Timestamp(year=base_date.year, month=base_date.month, day=base_date.day, hour=h, minute=m)
                        dt_list.append(dt)
                        last_hour = h
                    except:
                        dt_list.append(pd.NaT)
                else:
                    dt_list.append(pd.NaT)
            return dt_list

        # 1. Terapkan fungsi pembacaan waktu untuk setiap kolom Jam
        time_cols = ["Jam", "Jam Rotary B", "Jam Finish A", "Jam Finish B", "Jam Finish C"]
        for col in time_cols:
            if col in chart_data.columns:
                chart_data[f"{col}_dt"] = parse_time_sequence(chart_data[col])

        # 2. GRAFIK 1: TREN RM ROTARY MOIST
        fig_rm = go.Figure()
        df_rm_a = chart_data.dropna(subset=['Jam_dt', 'RM Rotary Moist A'])
        if not df_rm_a.empty:
            fig_rm.add_trace(go.Scatter(x=df_rm_a['Jam_dt'], y=df_rm_a['RM Rotary Moist A'], mode='lines+markers', name='RM Rotary A', line=dict(color='#3498db', width=3), marker=dict(size=8)))
        
        if 'Jam Rotary B_dt' in chart_data.columns:
            df_rm_b = chart_data.dropna(subset=['Jam Rotary B_dt', 'RM Rotary Moist B'])
            if not df_rm_b.empty:
                fig_rm.add_trace(go.Scatter(x=df_rm_b['Jam Rotary B_dt'], y=df_rm_b['RM Rotary Moist B'], mode='lines+markers', name='RM Rotary B', line=dict(color='#e74c3c', width=3), marker=dict(size=8)))
        
        fig_rm.update_layout(title="1. Tren RM Rotary Moist (Input)", xaxis_title="Jam Aktual", yaxis_title="Moisture (%)", hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0), xaxis=dict(tickformat="%H:%M"))

        # 3. GRAFIK 2: TREN ROTARY MOIST (PROCESS)
        fig_rot = go.Figure()
        df_rot_a = chart_data.dropna(subset=['Jam_dt', 'Rotary Moist A'])
        if not df_rot_a.empty:
            fig_rot.add_trace(go.Scatter(x=df_rot_a['Jam_dt'], y=df_rot_a['Rotary Moist A'], mode='lines+markers', name='Rotary A', line=dict(color='#9b59b6', width=3), marker=dict(size=8)))
        
        if 'Jam Rotary B_dt' in chart_data.columns:
            df_rot_b = chart_data.dropna(subset=['Jam Rotary B_dt', 'Rotary Moist B'])
            if not df_rot_b.empty:
                fig_rot.add_trace(go.Scatter(x=df_rot_b['Jam Rotary B_dt'], y=df_rot_b['Rotary Moist B'], mode='lines+markers', name='Rotary B', line=dict(color='#34495e', width=3), marker=dict(size=8)))
        
        fig_rot.update_layout(title="2. Tren Rotary Moist (Process)", xaxis_title="Jam Aktual", yaxis_title="Moisture (%)", hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0), xaxis=dict(tickformat="%H:%M"))

        # 4. GRAFIK 3: TREN FINISH PRODUCT MOIST (OUTPUT)
        fig_fin = go.Figure()
        if 'Jam Finish A_dt' in chart_data.columns:
            df_fin_a = chart_data.dropna(subset=['Jam Finish A_dt', 'Finish Moist A'])
            if not df_fin_a.empty:
                fig_fin.add_trace(go.Scatter(x=df_fin_a['Jam Finish A_dt'], y=df_fin_a['Finish Moist A'], mode='lines+markers', name='Finish Moist A', line=dict(color='#2ecc71', width=3), marker=dict(size=8)))
        
        if 'Jam Finish B_dt' in chart_data.columns:
            df_fin_b = chart_data.dropna(subset=['Jam Finish B_dt', 'Finish Moist B'])
            if not df_fin_b.empty:
                fig_fin.add_trace(go.Scatter(x=df_fin_b['Jam Finish B_dt'], y=df_fin_b['Finish Moist B'], mode='lines+markers', name='Finish Moist B', line=dict(color='#f1c40f', width=3), marker=dict(size=8)))
        
        if 'Jam Finish C_dt' in chart_data.columns:
            df_fin_c = chart_data.dropna(subset=['Jam Finish C_dt', 'Finish Moist C'])
            if not df_fin_c.empty:
                fig_fin.add_trace(go.Scatter(x=df_fin_c['Jam Finish C_dt'], y=df_fin_c['Finish Moist C'], mode='lines+markers', name='Finish Moist C', line=dict(color='#3498db', width=3), marker=dict(size=8)))
        
        fig_fin.update_layout(title="3. Tren Finish Product Moist (Output)", xaxis_title="Jam Aktual", yaxis_title="Moisture (%)", hovermode="x unified", legend=dict(orientation="h", y=1.1, x=0), xaxis=dict(tickformat="%H:%M"))

        # Merender ketiga grafik
        for fig in [fig_rm, fig_rot, fig_fin]:
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
            # Membuat background grafik elegan transparan menyatu dengan tema dark/light Streamlit
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, l=0, r=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.divider()
        
        # --- DOWNLOAD & TABEL ---
        csv = df_clean.drop(columns=[c for c in df_clean.columns if "_dt" in c]).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data Harian (CSV)",
            data=csv,
            file_name=f'laporan_produksi_{pilihan_bulan}_{pilihan_sheet}.csv',
            mime='text/csv',
        )

        st.subheader("🔍 Quality Control Data Check (🚦)")
        st.caption("INDIKATOR : 🔴DANGER | 🔵MEDIUM | 🟢SAFE QUALITY | 🟡WARNING")
        
        # ==========================================
        # 🚦 DEFINISI WARNA LAMPU QC (LENGKAP)
        # ==========================================
        def qc_highlight(row):
            styles = [''] * len(row)
            
            # 1. ROTARY MOIST (A & B)
            for col in ["Rotary Moist A", "Rotary Moist B"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        if val >= 16.0: styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;' # Merah
                        elif val >= 14.0: styles[idx] = 'background-color: #f1c40f; color: black; font-weight: bold;' # Kuning
                        else: styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;' # Hijau
                    except: pass

            # 2. FINISH MOIST (A, B, C)
            for col in ["Finish Moist A", "Finish Moist B", "Finish Moist C"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        if val > 15.0 or val < 5.0: styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;' # Merah
                        elif 13.51 <= val <= 15.00 or 5.00 <= val <= 7.99: styles[idx] = 'background-color: #f1c40f; color: black; font-weight: bold;' # Kuning
                        else: styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;' # Hijau
                    except: pass

            # 3. PARTICLE SIZE (A, B, C)
            for col in ["Finish Particle A", "Finish Particle B", "Finish Particle C"]:
                if col in df_clean.columns and pd.notnull(row[col]):
                    try:
                        val = float(row[col])
                        idx = df_clean.columns.get_loc(col)
                        
                        if val < 75.0: 
                            styles[idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;' # Merah
                        elif 75.0 <= val <= 79.9:
                            styles[idx] = 'background-color: #87CEFA; color: black; font-weight: bold;' # Biru Muda
                        elif 80.0 <= val <= 88.0:
                            styles[idx] = 'background-color: #2ecc71; color: black; font-weight: bold;' # Hijau
                        else: # > 88.0
                            styles[idx] = 'background-color: #f1c40f; color: black; font-weight: bold;' # Kuning
                    except: pass

            return styles

        # Tampilkan tabel dengan Warna QC, menyingkirkan kolom datetime bantuan
        cols_to_show = [c for c in df_clean.columns if "_dt" not in c]
        st.dataframe(df_clean[cols_to_show].style.apply(qc_highlight, axis=1), use_container_width=True)

    else:
        st.warning("⚠️ Data belum terinput.")

except Exception as e:
    st.warning(f"⚠️ Data belum terinput atau format belum sesuai.")
