
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Rekonsiliasi Invoice & Bank", layout="wide")

st.title("🔍 Sistem Rekonsiliasi Invoice & Rekening Koran")

# Upload
col1, col2 = st.columns(2)

with col1:
    invoice_file = st.file_uploader("📄 Upload File Invoice Penjualan (CSV/XLSX)", type=["csv", "xlsx"], key="invoice")
with col2:
    bank_file = st.file_uploader("🏦 Upload File Rekening Koran (CSV/XLSX)", type=["csv", "xlsx"], key="bank")

# Fungsi bantu baca file
def read_file(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    elif file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    return pd.DataFrame()

# Proses Rekonsiliasi
if invoice_file and bank_file:
    invoices = read_file(invoice_file)
    bank = read_file(bank_file)

    invoices.columns = invoices.columns.str.lower().str.strip()
    bank.columns = bank.columns.str.lower().str.strip()

    for df in [invoices, bank]:
        df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce')
        df['nominal'] = pd.to_numeric(df['nominal'], errors='coerce')

    matched = pd.merge(
        invoices, bank, 
        on=['nominal', 'tanggal'], 
        suffixes=('_inv', '_bank')
    )

    unmatched_invoice = invoices[~invoices.apply(tuple, 1).isin(matched[['nominal', 'tanggal']].apply(tuple, 1))]
    unmatched_bank = bank[~bank.apply(tuple, 1).isin(matched[['nominal', 'tanggal']].apply(tuple, 1))]

    st.subheader("✅ Transaksi Cocok")
    st.dataframe(matched)
    st.download_button("⬇️ Unduh Transaksi Cocok", matched.to_csv(index=False), file_name="matched.csv")

    st.subheader("❌ Invoice Belum Dibayar")
    st.dataframe(unmatched_invoice)
    st.download_button("⬇️ Unduh Invoice Belum Dibayar", unmatched_invoice.to_csv(index=False), file_name="unmatched_invoice.csv")

    st.subheader("❓ Mutasi Bank Tidak Dikenal")
    st.dataframe(unmatched_bank)
    st.download_button("⬇️ Unduh Mutasi Tak Dikenal", unmatched_bank.to_csv(index=False), file_name="unmatched_bank.csv")

else:
    st.info("Silakan unggah kedua file CSV atau Excel untuk melakukan rekonsiliasi.")

st.caption("📊 Dibuat dengan ❤️ oleh Code Copilot")
