
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
    all_dates_covered = set()
    for _, row in bank_df.iterrows():
        dates = extract_dates(row["Narasi"])
        if len(dates) == 1:
            d = dates[0]
            all_dates_covered.add(d)
            expanded_rows.append({'tanggal': d, 'kredit': row["Credit Transaction"], 'narasi': row["Narasi"]})
        elif len(dates) == 2:
            for d in pd.date_range(dates[0], dates[1]):
                all_dates_covered.add(d.date())
                expanded_rows.append({'tanggal': d.date(), 'kredit': None, 'narasi': row["Narasi"], 'kredit_grouped': row["Credit Transaction"]})

    expanded_bank_df = pd.DataFrame(expanded_rows)
    invoice_per_day = invoice_df.groupby('tanggal')['harga'].sum().reset_index()

    narasi_single = expanded_bank_df[expanded_bank_df['kredit'].notnull()]
    matched_single = pd.merge(narasi_single, invoice_per_day, on='tanggal', how='left')
    matched_single['selisih'] = (matched_single['kredit'] - matched_single['harga']).abs().fillna(matched_single['kredit'])

    narasi_multi = expanded_bank_df[expanded_bank_df['kredit'].isnull()]
    grouped = narasi_multi.groupby('narasi')['tanggal'].apply(list).reset_index()
    grouped = grouped.merge(bank_df[['Narasi', 'Credit Transaction']], left_on='narasi', right_on='Narasi', how='left')
    grouped['total_invoice'] = grouped['tanggal'].apply(
        lambda dates: invoice_per_day[invoice_per_day['tanggal'].isin(dates)]['harga'].sum()
    )
    grouped['selisih'] = (grouped['Credit Transaction'] - grouped['total_invoice']).abs()

    # Invoice yang tidak tercakup oleh narasi mana pun
    invoice_df['unmatched'] = ~invoice_df['tanggal'].isin(all_dates_covered)
    unmatched_invoices = invoice_df[invoice_df['unmatched']]

    st.sidebar.header("🔍 Filter Tanggal")
    start_date = st.sidebar.date_input("Tanggal Awal", value=min(invoice_df['tanggal']))
    end_date = st.sidebar.date_input("Tanggal Akhir", value=max(invoice_df['tanggal']))

    filtered_single = matched_single[
        (matched_single['tanggal'] >= start_date) & (matched_single['tanggal'] <= end_date)
    ]

    st.subheader("✅ Tabel Transaksi (Tanggal Tunggal)")
    st.dataframe(filtered_single[['tanggal', 'kredit', 'harga', 'selisih', 'narasi']])
    st.download_button("⬇️ Unduh CSV Tanggal Tunggal", filtered_single.to_csv(index=False), file_name="hasil_single.csv")

    filtered_group = grouped.copy()
    st.subheader("📆 Tabel Transaksi (Rentang Tanggal dari Narasi)")
    st.dataframe(filtered_group[['narasi', 'tanggal', 'Credit Transaction', 'total_invoice', 'selisih']])
    st.download_button("⬇️ Unduh CSV Rentang Narasi", filtered_group.to_csv(index=False), file_name="hasil_grouped.csv")

    total_selisih = filtered_single['selisih'].sum() + filtered_group['selisih'].sum()
    st.metric("💸 Total Selisih Semua", f"Rp {total_selisih:,.0f}".replace(",", "."))

    st.subheader("❗ Invoice Tidak Terhubung ke Narasi Manapun")
    st.dataframe(unmatched_invoices[['tanggal', 'harga', 'nama customer', 'nomer invoice']])
    st.download_button("⬇️ Unduh Invoice Tidak Cocok", unmatched_invoices.to_csv(index=False), file_name="invoice_unmatched.csv")

    st.success("🎉 Rekonsiliasi selesai!")

else:
    st.info("Silakan upload kedua file Excel di sidebar untuk memulai rekonsiliasi.")
