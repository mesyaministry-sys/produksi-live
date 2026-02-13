import streamlit as st
import pandas as pd
import numpy as np
import time

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ID FILE (PASTIKAN INI BENAR)
SHEET_ID_FEBRUARI = "1YQYvaRZzVttXVmo4PkF-qHP_rdVUXBAej-ryxgqwb8c"

# ==========================================
# 🛡️ SYSTEM UTILS
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .big-warning {
        padding: 20px; background-color: #ffebee; border: 2px solid #ff5252;
        color: #b71c1c; text-align: center; font-weight: bold; border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# LOGIN SEDERHANA (HARDCODED AGAR TIDAK RIBET SETUP SECRETS DULU)
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.warning("🔒 SYSTEM LOCKED")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("LOGIN"):
            if u=="mahesya13" and p=="swasa226":
                st.session_state["logged_in"] = True
                st.rerun()
            else: st.error("Salah")
    st.stop()

# ==========================================
# 📥 LOAD DATA (TANPA CACHE / TTL=0)
# ==========================================
# ⚠️ KUNCI PERBAIKAN: ttl=0 artinya "JANGAN SIMPAN DATA, AMBIL BARU TERUS"
@st.cache_data(ttl=0)
def load_data_realtime(sheet_name):
    # URL Construct
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_FEBRUARI}/gviz/tq?tqx=out:csv&sheet={sheet_name}'
    try:
        df = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)
        return df
    except:
        return None

# ==========================================
# 🖥️ UI DASHBOARD
# ==========================================
with st.sidebar:
    st.header("🎛️ KONTROL")
    # Pilihan Tanggal
    tgl = st.selectbox("Pilih Tanggal (Sheet):", [str(i) for i in range(1, 32)], index=0)
    
    st.divider()
    # TOMBOL DIAGNOSA
    st.caption("🔧 ALAT BANTU")
    if st.button("🗑️ HAPUS MEMORI (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()
        
    tampilkan_mentah = st.checkbox("Lihat Data Mentah (Raw)", value=True)
    
    st.divider()
    if st.button("LOGOUT"):
        st.session_state["logged_in"] = False
        st.rerun()

st.title(f"Laporan Harian: Tanggal {tgl} Februari")

# 1. AMBIL DATA
df_raw = load_data_realtime(tgl)

# 2. CEK APAKAH DATA ADA?
if df_raw is None or df_raw.empty:
    st.error("❌ Gagal mengambil data. Pastikan nama Sheet di Excel persis angkanya (misal '1', bukan '01').")
    st.stop()

# 3. CEK HEADER (APAKAH INI SHEET YG BENAR ATAU LEMPARAN GOOGLE?)
# Kita ambil 20 baris pertama, jadikan satu teks panjang
header_text = " ".join(df_raw.iloc[:20, :10].values.flatten()).upper()

# Logic Sederhana:
# Jika User pilih Tanggal 5, tapi di Excel tidak ada tulisan "5", curigai.
target_regex = rf"\b{tgl}\b" # Cari angka tanggal yg berdiri sendiri
ketemu_angka_tanggal = re.search(target_regex, header_text)

# TAMPILKAN HASIL DIAGNOSA (SUPAYA BAPAK PUAS MELIHAT ISINYA)
if tampilkan_mentah:
    st.info("👇 INI ADALAH DATA YANG DIKIRIM GOOGLE SAAT INI (REAL-TIME)")
    st.caption(f"Script membaca Sheet bernama: '{tgl}'")
    st.dataframe(df_raw.head(15)) # Tampilkan 15 baris pertama
    
    st.markdown("---")
    st.write("**🔍 Analisa Header Otomatis:**")
    st.text(f"Isi Header (Baris 1-20): {header_text[:200]}...")
    
    if ketemu_angka_tanggal:
        st.success(f"✅ Angka '{tgl}' ditemukan di Header Excel. Data kemungkinan benar.")
    else:
        st.error(f"⛔ Angka '{tgl}' TIDAK DITEMUKAN di Header. Google mungkin mengirim Sheet default (Tanggal 1).")

# ==========================================
# 4. PROSES VISUALISASI (Hanya jika lolos)
# ==========================================

# Cari baris jam 9:00
idx_900 = -1
col_jam = df_raw.iloc[:30, 0].astype(str)
matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]

if not matches.empty:
    idx_900 = matches.index[0]
    
    # Ambil Data Produksi
    # Asumsi struktur kolom stabil: 
    # Col 1=RM A, 2=Rotary A, 4=RM B, 5=Rotary B, 9=Ton A, 14=Ton B
    
    try:
        # Potong dataframe mulai dari jam 9
        df_prod = df_raw.iloc[idx_900:].copy()
        
        # Bersihkan data angka
        def clean_num(x):
            try: return float(str(x).replace(',', '.').strip())
            except: return 0.0
            
        ton_a = df_prod.iloc[:, 9].apply(clean_num).sum()
        ton_b = df_prod.iloc[:, 14].apply(clean_num).sum()
        total = ton_a + ton_b
        
        # JIKA TOTAL 0, TAMPILKAN PESAN KOSONG
        if total == 0:
             st.markdown('<div class="big-warning">⚠️ DATA KOSONG (0 TON)</div>', unsafe_allow_html=True)
             st.caption("Sheet ditemukan, tapi belum ada inputan angka produksi.")
        else:
            # TAMPILKAN DASHBOARD
            c1, c2, c3 = st.columns(3)
            c1.metric("Produksi Line A", f"{ton_a:,.0f} T")
            c2.metric("Produksi Line B", f"{ton_b:,.0f} T")
            c3.metric("TOTAL", f"{total:,.0f} T")
            
            # Tabel Traffic Light
            st.subheader("Data Detail")
            st.dataframe(df_prod.iloc[:, :15])

    except Exception as e:
        st.error(f"Gagal memproses data: {e}")

else:
    st.markdown("""
    <div class="big-warning">
        📂 BELUM ADA INPUTAN
    </div>
    <p style="text-align:center">Tidak ditemukan Jam 9:00 di sheet ini.</p>
    """, unsafe_allow_html=True)
