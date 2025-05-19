
import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="🔍 Rekonsiliasi ASDP", layout="wide")
st.markdown("""<h1 style='text-align: center;'>📊 Rekonsiliasi Invoice vs Rekening Koran ASDP</h1>""", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

def extract_dates(narasi):
    dates = re.findall(r"(\d{8})", str(narasi))
    return [datetime.strptime(d, "%Y%m%d").date() for d in dates]

st.sidebar.header("📁 Upload File Excel")
invoice_file = st.sidebar.file_uploader("📄 File Invoice", type=["xlsx"])
bank_file = st.sidebar.file_uploader("🏦 File Rekening Koran", type=["xlsx"])

if invoice_file and bank_file:
    st.success("✅ File berhasil diunggah!")

    invoice_df = pd.read_excel(invoice_file)
    bank_df = pd.read_excel(bank_file, header=11)

    invoice_df.columns = invoice_df.columns.str.lower().str.strip()
    invoice_df['tanggal'] = pd.to_datetime(invoice_df['tanggal inv']).dt.date
    invoice_df['harga'] = pd.to_numeric(invoice_df['harga'], errors='coerce')

    bank_df.columns = bank_df.columns.str.strip()
    if "Narasi" not in bank_df.columns or "Credit Transaction" not in bank_df.columns:
        st.error("❌ Kolom 'Narasi' atau 'Credit Transaction' tidak ditemukan.")
        st.stop()

    bank_df['Narasi'] = bank_df['Narasi'].astype(str)
    bank_df['Credit Transaction'] = bank_df['Credit Transaction'].astype(str).str.replace(",", "").astype(float)
    bank_df = bank_df.dropna(subset=["Narasi", "Credit Transaction"])

    expanded_rows = []
    for _, row in bank_df.iterrows():
        dates = extract_dates(row["Narasi"])
        if len(dates) == 1:
            expanded_rows.append({'tanggal': dates[0], 'kredit': row["Credit Transaction"], 'narasi': row["Narasi"]})
        elif len(dates) == 2:
            for d in pd.date_range(dates[0], dates[1]):
                expanded_rows.append({'tanggal': d.date(), 'kredit': None, 'narasi': row["Narasi"], 'kredit_grouped': row["Credit Transaction"]})

    expanded_bank_df = pd.DataFrame(expanded_rows)
    invoice_per_day = invoice_df.groupby('tanggal')['harga'].sum().reset_index()

    # Transaksi single date
    narasi_single = expanded_bank_df[expanded_bank_df['kredit'].notnull()]
    matched_single = pd.merge(narasi_single, invoice_per_day, on='tanggal', how='left')
    matched_single['status'] = matched_single.apply(
        lambda x: "✅ MATCH" if round(x['harga'], 2) == round(x['kredit'], 2) else "❌ MISMATCH", axis=1
    )

    # Transaksi multi-date
    narasi_multi = expanded_bank_df[expanded_bank_df['kredit'].isnull()]
    grouped = narasi_multi.groupby('narasi')['tanggal'].apply(list).reset_index()
    grouped = grouped.merge(bank_df[['Narasi', 'Credit Transaction']], left_on='narasi', right_on='Narasi', how='left')
    grouped['total_invoice'] = grouped['tanggal'].apply(
        lambda dates: invoice_per_day[invoice_per_day['tanggal'].isin(dates)]['harga'].sum()
    )
    grouped['status'] = grouped.apply(
        lambda x: "✅ MATCH" if round(x['total_invoice'], 2) == round(x['Credit Transaction'], 2) else "❌ MISMATCH", axis=1
    )

    st.subheader("📊 Ringkasan")
    colA, colB = st.columns(2)
    with colA:
        st.metric("💰 MATCH", f"{(matched_single['status'] == '✅ MATCH').sum() + (grouped['status'] == '✅ MATCH').sum()} transaksi")
    with colB:
        st.metric("⚠️ MISMATCH", f"{(matched_single['status'] == '❌ MISMATCH').sum() + (grouped['status'] == '❌ MISMATCH').sum()} transaksi")

    # Filter
    st.sidebar.header("🔍 Filter Hasil")
    selected_status = st.sidebar.multiselect("Status", ["✅ MATCH", "❌ MISMATCH"], default=["✅ MATCH", "❌ MISMATCH"])
    start_date = st.sidebar.date_input("Tanggal Awal", value=min(invoice_df['tanggal']))
    end_date = st.sidebar.date_input("Tanggal Akhir", value=max(invoice_df['tanggal']))

    filtered_single = matched_single[
        (matched_single['status'].isin(selected_status)) &
        (matched_single['tanggal'] >= start_date) &
        (matched_single['tanggal'] <= end_date)
    ]

    st.subheader("✅ Tabel Transaksi (Tanggal Tunggal)")
    st.dataframe(filtered_single[['tanggal', 'kredit', 'harga', 'status', 'narasi']])
    st.download_button("⬇️ Unduh CSV Tanggal Tunggal", filtered_single.to_csv(index=False), file_name="hasil_single.csv")

    filtered_group = grouped[grouped['status'].isin(selected_status)]
    st.subheader("📆 Tabel Transaksi (Rentang Tanggal Narasi)")
    st.dataframe(filtered_group[['narasi', 'tanggal', 'Credit Transaction', 'total_invoice', 'status']])
    st.download_button("⬇️ Unduh CSV Rentang Narasi", filtered_group.to_csv(index=False), file_name="hasil_grouped.csv")

    st.success("🎉 Rekonsiliasi selesai!")

else:
    st.info("Silakan upload kedua file Excel di sidebar untuk memulai rekonsiliasi.")
