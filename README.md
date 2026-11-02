# StockPilot

StockPilot is a Spanish-language portfolio prototype for small-business inventory and order tracking, built with Python and Streamlit.

## What it demonstrates

- Product and stock management
- Order creation and status tracking
- Customer records
- Inventory movement history
- Operational summaries and CSV exports

The included JSON files contain fictional sample records for demonstration. In the hosted portfolio demo, edits are kept only in the current visitor's Streamlit session; the sample files are never overwritten and changes are not shared between visitors.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Project status and limitations

This is a portfolio prototype. It does not include user accounts, role-based access, a hosted database, backups, or production multi-user controls. The hosted demo keeps visitor edits only in session memory and starts from the fictional sample data; do not enter confidential or real customer information. A production deployment would need a separately scoped security, persistence, and hosting design.
