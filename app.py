
import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard ASDP", layout="wide")
conn = sqlite3.connect("asdp.db", check_same_thread=False)

MENU_ITEMS = [
    "Dashboard",
    "Tiket Terjual",
    "Penambahan & Pengurangan",
    "Naik/Turun Golongan",
    "Rekonsiliasi"
]
menu = st.sidebar.radio("Pilih Halaman", MENU_ITEMS)

if menu == "Dashboard":
    st.title("📊 Dashboard Rekapitulasi Sales Channel")
    st.markdown("### Pilih Periode untuk Masing-Masing Komponen")

    col1, col2 = st.columns(2)
    with col1:
        tgl_tiket_start = st.date_input("Tiket Terjual - Tanggal Mulai", key="tgl_tt1")
        tgl_tiket_end = st.date_input("Tiket Terjual - Tanggal Selesai", key="tgl_tt2")
    with col2:
        tgl_penambahan = st.date_input("Penambahan - Tanggal", key="tgl_p")
        tgl_pengurangan = st.date_input("Pengurangan - Tanggal", key="tgl_m")

    col3, col4 = st.columns(2)
    with col3:
        tgl_gol_start = st.date_input("Naik/Turun Golongan - Tanggal Mulai", key="tgl_g1")
    with col4:
        tgl_gol_end = st.date_input("Naik/Turun Golongan - Tanggal Selesai", key="tgl_g2")

    pelabuhan = ['MERAK', 'BAKAUHENI', 'KETAPANG', 'GILIMANUK']
    df_tiket = pd.read_sql("SELECT * FROM tiket_terjual", conn)
    df_penambahan = pd.read_sql("SELECT * FROM penambahan", conn)
    df_pengurangan = pd.read_sql("SELECT * FROM pengurangan", conn)
    df_golongan = pd.read_sql("SELECT * FROM golongan", conn)

    t_tiket = df_tiket[(pd.to_datetime(df_tiket['tanggal_mulai']) >= pd.to_datetime(tgl_tiket_start)) &
                       (pd.to_datetime(df_tiket['tanggal_selesai']) <= pd.to_datetime(tgl_tiket_end))]
    t_penambahan = df_penambahan[pd.to_datetime(df_penambahan['tanggal']) == pd.to_datetime(tgl_penambahan)]
    t_pengurangan = df_pengurangan[pd.to_datetime(df_pengurangan['tanggal']) == pd.to_datetime(tgl_pengurangan)]
    t_golongan = df_golongan[(pd.to_datetime(df_golongan['tanggal_mulai']) >= pd.to_datetime(tgl_gol_start)) &
                              (pd.to_datetime(df_golongan['tanggal_selesai']) <= pd.to_datetime(tgl_gol_end))]

    tiket = t_tiket.groupby('pelabuhan')['jumlah'].sum().reindex(pelabuhan, fill_value=0)
    penambahan = t_penambahan.groupby('pelabuhan')['nilai'].sum().reindex(pelabuhan, fill_value=0)
    pengurangan = t_pengurangan.groupby('pelabuhan')['nilai'].sum().reindex(pelabuhan, fill_value=0)

    df_invoice = pd.read_sql("SELECT * FROM golongan", conn)
    df_invoice = df_invoice[(pd.to_datetime(df_invoice['tanggal_mulai']) >= pd.to_datetime(tgl_gol_start)) &
                            (pd.to_datetime(df_invoice['tanggal_selesai']) <= pd.to_datetime(tgl_gol_end))]
    df_invoice['pelabuhan'] = df_invoice['pelabuhan'].str.upper().str.strip()
    df_invoice = df_invoice[df_invoice['pelabuhan'].isin(pelabuhan)]
    df_gol = df_invoice.groupby('pelabuhan')['nilai'].sum().reindex(pelabuhan, fill_value=0)

    pinbuk = tiket + penambahan - pengurangan + df_gol

    df_rekap = pd.DataFrame({
        'Pelabuhan Asal': pelabuhan,
        'Tiket Terjual': tiket.values,
        'Penambahan': penambahan.values,
        'Pengurangan': pengurangan.values,
        'Naik/Turun Golongan': df_gol.values,
        'Nominal Pinbuk': pinbuk.values
    })

    for col in df_rekap.columns[1:]:
        df_rekap[col] = df_rekap[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))

    total = {
        'Pelabuhan Asal': 'TOTAL',
        'Tiket Terjual': df_rekap['Tiket Terjual'].str.replace("Rp ", "").str.replace(".", "").astype(int).sum(),
        'Penambahan': df_rekap['Penambahan'].str.replace("Rp ", "").str.replace(".", "").astype(int).sum(),
        'Pengurangan': df_rekap['Pengurangan'].str.replace("Rp ", "").str.replace(".", "").astype(int).sum(),
        'Naik/Turun Golongan': df_rekap['Naik/Turun Golongan'].str.replace("Rp ", "").str.replace(".", "").astype(int).sum(),
        'Nominal Pinbuk': df_rekap['Nominal Pinbuk'].str.replace("Rp ", "").str.replace(".", "").astype(int).sum()
    }

    for key in total.keys():
        if key != 'Pelabuhan Asal':
            total[key] = f"Rp {total[key]:,.0f}".replace(",", ".")

    df_rekap = pd.concat([df_rekap, pd.DataFrame([total])], ignore_index=True)
    st.dataframe(df_rekap, use_container_width=True)






elif menu == "Tiket Terjual":
    st.title("🎟️ Tiket Terjual")

    files = st.file_uploader("Upload File Tiket (boleh banyak)", type=["xlsx"], accept_multiple_files=True)
    if files:
        hasil = []
        semua_tanggal = []

        for f in files:
            try:
                df_raw = pd.read_excel(f, header=None)
                pelabuhan = str(df_raw.iloc[2, 1]).strip().upper()
                jumlah = pd.to_numeric(df_raw.iloc[11:, 4].dropna().iloc[-1], errors='coerce')
                tanggal = pd.to_datetime(df_raw.iloc[11:, 2].dropna(), errors='coerce')
                if not tanggal.empty:
                    semua_tanggal.append(tanggal.min().date())
                    semua_tanggal.append(tanggal.max().date())
                if pd.notnull(jumlah):
                    hasil.append({'Pelabuhan Asal': pelabuhan, 'Jumlah': int(jumlah)})
            except Exception as e:
                st.error(f"❌ Gagal memproses {f.name}: {e}")

        if hasil:
            if semua_tanggal:
                p1 = min(semua_tanggal)
                p2 = max(semua_tanggal)
                st.markdown(f"**Periode: {p1.strftime('%d %B %Y')} s.d. {p2.strftime('%d %B %Y')}**")

            df = pd.DataFrame(hasil)
            urutan = ['MERAK', 'BAKAUHENI', 'KETAPANG', 'GILIMANUK']
            df = df.groupby('Pelabuhan Asal')['Jumlah'].sum().reindex(urutan, fill_value=0).reset_index()
            total = df['Jumlah'].sum()
            df['Jumlah'] = df['Jumlah'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            df = pd.concat([df, pd.DataFrame([{'Pelabuhan Asal': 'TOTAL', 'Jumlah': f"Rp {total:,.0f}".replace(",", ".")}])])
            st.dataframe(df.style.set_properties(subset=['Jumlah'], **{'text-align': 'right'}), use_container_width=True)
        else:
            st.warning("Tidak ada data valid ditemukan.")
    else:
        st.info("Silakan upload file tiket.")


elif menu == "Penambahan & Pengurangan":
    st.title("📈 Penambahan dan 📉 Pengurangan Tarif")

    file = st.file_uploader("Upload File Excel (boarding pass)", type=["xlsx"])
    if file:
        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip().str.upper()

            df['JAM'] = pd.to_numeric(df['JAM'], errors='coerce')
            df['CETAK BOARDING PASS'] = pd.to_datetime(df['CETAK BOARDING PASS'], errors='coerce')
            df['ASAL'] = df['ASAL'].str.upper().str.strip()
            df['TARIF'] = pd.to_numeric(df['TARIF'], errors='coerce')

            df = df[df['JAM'].between(0, 7)]
            df = df.dropna(subset=['CETAK BOARDING PASS'])

            col1, col2 = st.columns(2)
            with col1:
                tanggal_penambahan = st.date_input("Tanggal Penambahan", key="tgl_penambahan")
            with col2:
                tanggal_pengurangan = st.date_input("Tanggal Pengurangan", key="tgl_pengurangan")

            pelabuhan = ['MERAK', 'BAKAUHENI', 'KETAPANG', 'GILIMANUK']
            df_p = df[df['CETAK BOARDING PASS'].dt.date == tanggal_penambahan]
            df_m = df[df['CETAK BOARDING PASS'].dt.date == tanggal_pengurangan]

            p_group = df_p.groupby('ASAL')['TARIF'].sum().reindex(pelabuhan, fill_value=0)
            m_group = df_m.groupby('ASAL')['TARIF'].sum().reindex(pelabuhan, fill_value=0)

            df_final = pd.DataFrame({
                'Pelabuhan Asal': pelabuhan,
                'Penambahan': p_group.values,
                'Pengurangan': m_group.values
            })

            for col in ['Penambahan', 'Pengurangan']:
                df_final[col] = df_final[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))

            total_row = {
                'Pelabuhan Asal': 'TOTAL',
                'Penambahan': f"Rp {p_group.sum():,.0f}".replace(",", "."),
                'Pengurangan': f"Rp {m_group.sum():,.0f}".replace(",", ".")
            }

            df_final = pd.concat([df_final, pd.DataFrame([total_row])], ignore_index=True)
            st.dataframe(df_final, use_container_width=True)
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")
    else:
        st.info("Silakan upload file boarding pass.")


elif menu == "Naik/Turun Golongan":
    st.title("🚐 Naik/Turun Golongan")

    f_inv = st.file_uploader("Upload File Invoice", type=["xlsx"], key="gol_inv")
    f_tik = st.file_uploader("Upload File Tiket Summary", type=["xlsx"], key="gol_tik")

    if f_inv and f_tik:
        try:
            df_inv = pd.read_excel(f_inv, header=1)
            df_tik = pd.read_excel(f_tik, header=1)

            df_inv.columns = df_inv.columns.str.upper().str.strip()
            df_tik.columns = df_tik.columns.str.upper().str.strip()

            invoice_col = 'NOMER INVOICE' if 'NOMER INVOICE' in df_inv.columns else 'NOMOR INVOICE'
            df_inv['INVOICE'] = df_inv[invoice_col].astype(str).str.strip()
            df_tik['INVOICE'] = df_tik['NOMOR INVOICE'].astype(str).str.strip()

            df_inv['NILAI'] = pd.to_numeric(df_inv['HARGA'], errors='coerce')
            df_tik['NILAI'] = pd.to_numeric(df_tik['TARIF'], errors='coerce') * -1

            df1 = df_inv[['INVOICE', 'KEBERANGKATAN', 'NILAI']].rename(columns={'KEBERANGKATAN': 'Pelabuhan'})
            df2 = df_tik[['INVOICE', 'NILAI']]
            df2['Pelabuhan'] = None

            df_all = pd.concat([df1, df2], ignore_index=True)
            df_all['Pelabuhan'] = df_all['Pelabuhan'].fillna(method='ffill')
            df_all['Pelabuhan'] = df_all['Pelabuhan'].str.upper().str.strip()

            df_group = df_all.groupby(['INVOICE', 'Pelabuhan'])['NILAI'].sum().reset_index()
            df_filtered = df_group[df_group['Pelabuhan'].isin(['MERAK', 'BAKAUHENI', 'KETAPANG', 'GILIMANUK'])]

            df_sum = df_filtered.groupby('Pelabuhan')['NILAI'].sum().reset_index()
            df_sum = df_sum[df_sum['NILAI'] != 0]
            df_sum['Keterangan'] = df_sum['NILAI'].apply(lambda x: "Turun Golongan" if x > 0 else "Naik Golongan")
            df_sum['Selisih Naik/Turun Golongan'] = df_sum['NILAI'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            df_sum = df_sum[['Pelabuhan', 'Selisih Naik/Turun Golongan', 'Keterangan']].rename(columns={'Pelabuhan': 'Pelabuhan Asal'})

            total = df_filtered['NILAI'].sum()
            df_total = pd.DataFrame([{
                'Pelabuhan Asal': 'TOTAL',
                'Selisih Naik/Turun Golongan': f"Rp {total:,.0f}".replace(",", "."),
                'Keterangan': ''
            }])

            df_final = pd.concat([df_sum, df_total], ignore_index=True)
            st.dataframe(df_final, use_container_width=True)
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")
    else:
        st.info("Silakan upload file invoice dan tiket.")


elif menu == "Rekonsiliasi":
    st.title("💸 Rekonsiliasi Invoice vs Rekening")

    f_inv = st.file_uploader("Upload File Invoice", type=["xlsx"], key="rinv")
    f_bank = st.file_uploader("Upload File Rekening Koran", type=["xlsx"], key="rbank")

    if f_inv and f_bank:
        try:
            df_inv = pd.read_excel(f_inv)
            df_bank = pd.read_excel(f_bank, skiprows=11)

            df_inv.columns = df_inv.columns.str.lower().str.strip()
            df_bank.columns = df_bank.columns.str.lower().str.strip()

            df_inv = df_inv[['tanggal invoice', 'harga']].dropna()
            df_inv['tanggal invoice'] = pd.to_datetime(df_inv['tanggal invoice'], errors='coerce')
            df_inv['harga'] = pd.to_numeric(df_inv['harga'], errors='coerce')
            df_inv['tanggal'] = df_inv['tanggal invoice'].dt.date

            df_bank = df_bank[['narasi', 'credit transaction']].dropna()
            df_bank['credit transaction'] = pd.to_numeric(df_bank['credit transaction'], errors='coerce')

            records = []
            for _, row in df_bank.iterrows():
                narasi = str(row['narasi'])
                kredit = row['credit transaction']
                tanggal_r = None
                invoice_total = 0

                match = re.search(r'(20\d{6})\s*[-–]?\s*(20\d{6})?', narasi)
                if match:
                    start = pd.to_datetime(match.group(1), format='%Y%m%d', errors='coerce')
                    end = pd.to_datetime(match.group(2), format='%Y%m%d', errors='coerce') if match.group(2) else start
                    if pd.notnull(start) and pd.notnull(end):
                        rng = pd.date_range(start, end)
                        invoice_total = df_inv[df_inv['tanggal'].isin(rng.date)]['harga'].sum()
                        tanggal_r = start.date()

                if tanggal_r:
                    selisih = invoice_total - kredit
                    records.append({
                        'Tanggal': tanggal_r,
                        'Narasi': narasi,
                        'Nominal Kredit': kredit,
                        'Nominal Invoice': invoice_total,
                        'Selisih': selisih
                    })

            df_rekon = pd.DataFrame(records)
            df_rekon[['Nominal Kredit', 'Nominal Invoice', 'Selisih']] = df_rekon[['Nominal Kredit', 'Nominal Invoice', 'Selisih']].fillna(0)
            for col in ['Nominal Kredit', 'Nominal Invoice', 'Selisih']:
                df_rekon[col] = df_rekon[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))

            styled = df_rekon.style.set_properties(subset=['Nominal Kredit', 'Nominal Invoice', 'Selisih'], **{'text-align': 'right'})
            st.dataframe(styled, use_container_width=True)
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")
    else:
        st.info("Silakan upload file invoice dan rekening.")
