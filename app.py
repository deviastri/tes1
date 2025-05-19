
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Rekonsiliasi Excel - Invoice & Bank", layout="wide")

st.title("📊 Rekonsiliasi Data Invoice dan Rekening Koran (Excel Only)")

col1, col2 = st.columns(2)

with col1:
    invoice_file = st.file_uploader("📁 Upload File Invoice (.xlsx)", type=["xlsx"], key="invoice")
with col2:
    bank_file = st.file_uploader("🏦 Upload File Rekening Koran (.xlsx)", type=["xlsx"], key="bank")

if invoice_file and bank_file:
    try:
        invoices = pd.read_excel(invoice_file)
        bank = pd.read_excel(bank_file)

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

        st.success("✅ Rekonsiliasi Berhasil")

        st.subheader("✅ Transaksi Cocok")
        st.dataframe(matched)
        st.download_button("⬇️ Unduh Transaksi Cocok", matched.to_csv(index=False), file_name="matched.csv")

        st.subheader("❌ Invoice Belum Dibayar")
        st.dataframe(unmatched_invoice)
        st.download_button("⬇️ Unduh Invoice Belum Dibayar", unmatched_invoice.to_csv(index=False), file_name="unmatched_invoice.csv")

        st.subheader("❓ Mutasi Bank Tidak Dikenal")
        st.dataframe(unmatched_bank)
        st.download_button("⬇️ Unduh Mutasi Tak Dikenal", unmatched_bank.to_csv(index=False), file_name="unmatched_bank.csv")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat membaca atau memproses file: {e}")

else:
    st.info("Silakan unggah kedua file Excel (.xlsx) untuk memulai rekonsiliasi.")

st.caption("📁 Dibuat dengan ❤️ oleh Code Copilot - Versi Excel Only")
