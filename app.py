
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




