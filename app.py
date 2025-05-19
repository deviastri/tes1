
import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Rekonsiliasi ASDP Excel", layout="wide")
st.title("📊 Rekonsiliasi Invoice & Rekening Koran ASDP (Excel)")

# Fungsi parsing tanggal dari narasi rekening koran
def extract_dates(narasi):
    dates = re.findall(r"(\d{8})", str(narasi))
    return [datetime.strptime(d, "%Y%m%d").date() for d in dates]

def expand_narasi_rows(df):
    rows = []
    for _, row in df.iterrows():
        dates = extract_dates(row['narasi'])
        if not dates:
            continue
        if len(dates) == 1:
            rows.append({'tanggal': dates[0], 'kredit': row['kredit'], 'narasi': row['narasi']})
        elif len(dates) == 2:
            start, end = dates
            while start <= end:
                rows.append({'tanggal': start, 'kredit': None, 'narasi': row['narasi'], 'id': id})
                start += pd.Timedelta(days=1)
    return pd.DataFrame(rows)

col1, col2 = st.columns(2)

with col1:
    invoice_file = st.file_uploader("📥 Upload Invoice Excel", type=["xlsx"])
with col2:
    bank_file = st.file_uploader("🏦 Upload Rekening Koran Excel", type=["xlsx"])

if invoice_file and bank_file:
    invoice_df = pd.read_excel(invoice_file)
    bank_df = pd.read_excel(bank_file)

    # Normalisasi kolom invoice
    invoice_df.columns = invoice_df.columns.str.lower().str.strip()
    invoice_df['tanggal'] = pd.to_datetime(invoice_df['tanggal inv']).dt.date
    invoice_df['harga'] = pd.to_numeric(invoice_df['harga'], errors='coerce')

    # Normalisasi kolom rekening koran
    bank_df.columns = bank_df.columns.str.lower().str.strip()
    bank_df = bank_df.rename(columns=lambda x: x.lower())
    bank_df = bank_df.rename(columns={'kredit': 'kredit', 'narasi': 'narasi'})
    bank_df = bank_df.dropna(subset=['kredit', 'narasi'])

    expanded_rows = []

    for _, row in bank_df.iterrows():
        dates = extract_dates(row['narasi'])
        if len(dates) == 1:
            expanded_rows.append({'tanggal': dates[0], 'kredit': row['kredit'], 'narasi': row['narasi']})
        elif len(dates) == 2:
            date_range = pd.date_range(start=dates[0], end=dates[1])
            for d in date_range:
                expanded_rows.append({'tanggal': d.date(), 'kredit': None, 'narasi': row['narasi'], 'kredit_grouped': row['kredit']})

    expanded_bank_df = pd.DataFrame(expanded_rows)

    # Hitung total invoice per tanggal
    invoice_per_day = invoice_df.groupby('tanggal')['harga'].sum().reset_index()

    # Gabungkan transaksi narasi single-date
    narasi_single = expanded_bank_df[expanded_bank_df['kredit'].notnull()]
    matched_single = pd.merge(narasi_single, invoice_per_day, on='tanggal', how='left')
    matched_single['status'] = matched_single.apply(
        lambda x: "MATCH" if round(x['harga'], 2) == round(x['kredit'], 2) else "MISMATCH", axis=1
    )

    # Gabungkan transaksi narasi multi-date
    narasi_multi = expanded_bank_df[expanded_bank_df['kredit'].isnull()]
    grouped = narasi_multi.groupby('narasi')['tanggal'].apply(list).reset_index()
    grouped = grouped.merge(
        bank_df[['narasi', 'kredit']], on='narasi', how='left'
    ).drop_duplicates()

    def sum_invoice_for_dates(dates):
        return invoice_per_day[invoice_per_day['tanggal'].isin(dates)]['harga'].sum()

    grouped['total_invoice'] = grouped['tanggal'].apply(sum_invoice_for_dates)
    grouped['status'] = grouped.apply(
        lambda x: "MATCH" if round(x['total_invoice'], 2) == round(x['kredit'], 2) else "MISMATCH", axis=1
    )

    st.subheader("✅ Transaksi Single Date")
    st.dataframe(matched_single[['tanggal', 'kredit', 'harga', 'status', 'narasi']])

    st.subheader("📆 Transaksi Multi Date (Rentang Tanggal dari Narasi)")
    st.dataframe(grouped[['narasi', 'tanggal', 'kredit', 'total_invoice', 'status']])

    st.success("Rekonsiliasi selesai! ✅")

else:
    st.info("Silakan upload kedua file Excel untuk memulai.")
