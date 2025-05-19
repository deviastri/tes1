
import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Rekonsiliasi ASDP Excel", layout="wide")
st.title("📊 Rekonsiliasi Invoice & Rekening Koran ASDP (Excel)")

def extract_dates(narasi):
    dates = re.findall(r"(\d{8})", str(narasi))
    return [datetime.strptime(d, "%Y%m%d").date() for d in dates]

col1, col2 = st.columns(2)

with col1:
    invoice_file = st.file_uploader("📥 Upload Invoice Excel", type=["xlsx"])
with col2:
    bank_file = st.file_uploader("🏦 Upload Rekening Koran Excel", type=["xlsx"])

if invoice_file and bank_file:
    invoice_df = pd.read_excel(invoice_file)
    bank_df = pd.read_excel(bank_file, header=11)  # Baca mulai baris ke-12

    invoice_df.columns = invoice_df.columns.str.lower().str.strip()
    invoice_df['tanggal'] = pd.to_datetime(invoice_df['tanggal inv']).dt.date
    invoice_df['harga'] = pd.to_numeric(invoice_df['harga'], errors='coerce')

    bank_df.columns = bank_df.columns.str.strip()
    if "Narasi" not in bank_df.columns or "Credit Transaction" not in bank_df.columns:
        st.error("Kolom 'Narasi' atau 'Credit Transaction' tidak ditemukan.")
        st.stop()

    bank_df['Narasi'] = bank_df['Narasi'].astype(str)
    # Bersihkan format angka dari koma dan titik
    bank_df['Credit Transaction'] = bank_df['Credit Transaction'].astype(str).str.replace(",", "").astype(float)
    bank_df = bank_df.dropna(subset=["Narasi", "Credit Transaction"])

    expanded_rows = []
    for _, row in bank_df.iterrows():
        dates = extract_dates(row["Narasi"])
        if len(dates) == 1:
            expanded_rows.append({'tanggal': dates[0], 'kredit': row["Credit Transaction"], 'narasi': row["Narasi"]})
        elif len(dates) == 2:
            date_range = pd.date_range(start=dates[0], end=dates[1])
            for d in date_range:
                expanded_rows.append({'tanggal': d.date(), 'kredit': None, 'narasi': row["Narasi"], 'kredit_grouped': row["Credit Transaction"]})

    expanded_bank_df = pd.DataFrame(expanded_rows)

    invoice_per_day = invoice_df.groupby('tanggal')['harga'].sum().reset_index()

    # Transaksi 1 tanggal
    narasi_single = expanded_bank_df[expanded_bank_df['kredit'].notnull()]
    matched_single = pd.merge(narasi_single, invoice_per_day, on='tanggal', how='left')
    matched_single['status'] = matched_single.apply(
        lambda x: "MATCH" if round(x['harga'], 2) == round(x['kredit'], 2) else "MISMATCH", axis=1
    )

    # Transaksi rentang tanggal
    narasi_multi = expanded_bank_df[expanded_bank_df['kredit'].isnull()]
    grouped = narasi_multi.groupby('narasi')['tanggal'].apply(list).reset_index()
    grouped = grouped.merge(bank_df[['Narasi', 'Credit Transaction']], left_on='narasi', right_on='Narasi', how='left')
    grouped['total_invoice'] = grouped['tanggal'].apply(lambda dates: invoice_per_day[invoice_per_day['tanggal'].isin(dates)]['harga'].sum())
    grouped['status'] = grouped.apply(
        lambda x: "MATCH" if round(x['total_invoice'], 2) == round(x['Credit Transaction'], 2) else "MISMATCH", axis=1
    )

    st.subheader("✅ Transaksi Single Date")
    st.dataframe(matched_single[['tanggal', 'kredit', 'harga', 'status', 'narasi']])

    st.subheader("📆 Transaksi Multi Date (Rentang Tanggal dari Narasi)")
    st.dataframe(grouped[['narasi', 'tanggal', 'Credit Transaction', 'total_invoice', 'status']])

    st.success("Rekonsiliasi selesai!")

else:
    st.info("Silakan upload kedua file Excel untuk memulai.")
