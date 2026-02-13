import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# ⚙️ KONFIGURASI
# ==========================================
st.set_page_config(page_title="Monitoring Produksi BE", layout="wide", page_icon="🏭")

# ID FILE MASTER (Sesuai Link Terakhir Anda)
SHEET_ID = "1MQsvhmWmrGNtp3Txh07Z-88VfgEZTj_WBD5zLNs9GGY"

# ==========================================
# 🛡️ STYLE & LOGIN
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stat-box { padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; font-weight: bold; }
    .stat-ok { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #4caf50; }
    .stat-warn { background-color: #fff3e0; color: #ef6c00; border: 1px solid #ff9800; }
    .stat-err { background-color: #ffebee; color: #c62828; border: 1px solid #ef5350; }
    </style>
""", unsafe_allow_html=True)

# Login Sederhana
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if not st.session_state["logged_in"]:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.info("🔒 SYSTEM LOCKED")
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        if st.button("LOGIN"):
            if u=="mahesya13" and p=="swasa226": st.session_state["logged_in"] = True; st.rerun()
            else: st.error("Salah")
    st.stop()

# ==========================================
# 🎛️ MENU NAVIGASI
# ==========================================
with st.sidebar:
    st.header("🗂️ PILIH LAPORAN")
    
    # 1. Pilih Bulan (Format Singkatan sesuai nama sheet Anda: Jan, Feb)
    # Dictionary: Nama Tampil -> Kode di Sheet
    map_bulan = {"JANUARI": "Jan", "FEBRUARI": "Feb", "MARET": "Mar"}
    pilih_bln = st.selectbox("Bulan:", list(map_bulan.keys()), index=1) # Default Februari
    kode_bln = map_bulan[pilih_bln]
    
    # 2. Pilih Tanggal
    pilih_tgl = st.selectbox("Tanggal:", [str(i) for i in range(1, 32)], index=3) # Default tgl 4
    
    # Gabungkan jadi Nama Sheet: "4 Feb"
    target_sheet = f"{pilih_tgl} {kode_bln}"
    
    st.divider()
    st.caption(f"📂 Membuka Sheet: **'{target_sheet}'**")
    
    if st.button("🔄 REFRESH"): st.cache_data.clear(); st.rerun()
    if st.button("LOGOUT"): st.session_state["logged_in"] = False; st.rerun()

st.title(f"Laporan: {target_sheet} 2026")

# ==========================================
# 📥 LOAD DATA
# ==========================================
url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={target_sheet}'

try:
    # Coba tarik data
    df_raw = pd.read_csv(url, header=None, dtype=str, keep_default_na=False)
    
    # === VALIDASI SHEET NYASAR ===
    # Google kadang melempar sheet pertama ("1 Jan") kalau sheet yg diminta ("5 Feb") gak ada.
    # Kita cek Header Excel baris-baris awal.
    # Harus ada tulisan nama bulan yang benar (Misal "Feb").
    
    header_text = " ".join(df_raw.iloc[:10].astype(str).values.flatten()).upper()
    
    # Cek Validitas: Apakah Kode Bulan (FEB) ada di header?
    if kode_bln.upper() in header_text:
        is_sheet_valid = True
    else:
        # Kalau kita minta "5 Feb", tapi header isinya "1 JAN", berarti sheet gak ada.
        is_sheet_valid = False

    # === PROSES DATA ===
    if is_sheet_valid:
        # Cari baris Jam 9:00
        idx_900 = -1
        col_jam = df_raw.iloc[:30, 0].astype(str)
        matches = col_jam[col_jam.str.contains(r"9[:\.]00", regex=True)]
        
        if not matches.empty:
            idx_900 = matches.index[0]
            df = df_raw.iloc[idx_900:].copy()
            
            # Fungsi Bersih Angka
            def clean(x):
                try: return float(str(x).replace(',', '.').strip())
                except: return 0.0

            # Mapping Kolom (Hardcode sesuai posisi di file Anda)
            # Kolom 9 = Tonnage A, Kolom 14 = Tonnage B
            # Kolom 1 = RM A, Kolom 2 = Rotary A
            
            ton_a = df.iloc[:, 9].apply(clean).sum()
            ton_b = df.iloc[:, 14].apply(clean).sum()
            total = ton_a + ton_b
            
            rm_avg = df.iloc[:, 1].apply(clean).mean()
            
            if total == 0 and rm_avg == 0:
                st.markdown(f'<div class="stat-box stat-warn">⚠️ SHEET ADA, TAPI DATA MASIH KOSONG</div>', unsafe_allow_html=True)
                st.caption("Operator belum menginput angka produksi di sheet ini.")
            else:
                st.markdown(f'<div class="stat-box stat-ok">✅ DATA DITEMUKAN</div>', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Produksi Line A", f"{ton_a:,.0f} T")
                c2.metric("Produksi Line B", f"{ton_b:,.0f} T")
                c3.metric("TOTAL", f"{total:,.0f} T")
                
                st.divider()
                st.subheader("Detail")
                st.dataframe(df.iloc[:, :15].head(15), use_container_width=True)
                
        else:
            # Sheet ada (namanya benar), tapi format tabel (Jam 9:00) belum dicopy/rusak
            st.warning(f"⚠️ Sheet '{target_sheet}' ditemukan, tapi format tabel (Jam 9:00) tidak terbaca.")
            st.dataframe(df_raw.head(10)) # Tampilkan raw biar tau salahnya dmn
            
    else:
        # Sheet tidak ditemukan -> Google lempar sheet lain
        st.markdown(f"""
        <div class="stat-box stat-err">
            ⛔ DATA TIDAK TERSEDIA
        </div>
        """, unsafe_allow_html=True)
        st.error(f"Sheet bernama **'{target_sheet}'** belum dibuat di Excel.")
        st.info("Tips: Pastikan nama Tab di Google Sheet persis: 'Angka Spasi 3HurufBulan' (Contoh: 5 Feb).")

except Exception as e:
    # Error ini muncul jika Google benar-benar tidak menemukan sheet dan return 404/Error
    st.markdown(f"""
    <div class="stat-box stat-err">
        ⛔ SHEET BELUM DIBUAT
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"Sistem tidak menemukan Tab bernama **'{target_sheet}'** di file Master.")
