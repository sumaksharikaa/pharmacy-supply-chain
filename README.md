# 🏭 Pharmacy Supply Chain & Prescription Analytics

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://postgresql.org)
[![Oracle SQL](https://img.shields.io/badge/Oracle--Compatible%20SQL-red?logo=oracle)](https://oracle.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?logo=streamlit)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-5.22-purple?logo=plotly)](https://plotly.com)

An end-to-end **Pharmacy Supply Chain & Prescription Analytics** platform covering drug inventory management, supplier performance, prescription fill rate tracking, stockout analysis, and automated reorder alerts. Built with Oracle-compatible SQL, PostgreSQL, Python ETL, and Streamlit.

---

## 🗂️ Project Structure

```
pharmacy-supply-chain/
├── data/
│   └── generate_data.py              # Synthetic supply chain data generator
├── sql/
│   ├── schema.sql                    # Oracle-compatible PostgreSQL schema
│   └── analytics_queries.sql         # 11 KPI queries with window functions
├── etl/
│   └── etl_pipeline.py               # ETL with inventory reconciliation
├── app/
│   └── app.py                        # Streamlit dashboard (5 tabs)
├── requirements.txt
└── README.md
```

---

## 🏗️ ER Model

```
suppliers ──────────────────────────────┐
    │                                   │
    ▼                                   ▼
  drugs ──────► inventory          purchase_orders
    │               │
    ▼               ▼
prescriptions   stockout_events
    │
    ▼
warehouses (shared FK)
```

---

## 📊 Dashboard Features

| Tab | What it shows |
|---|---|
| **📦 Inventory** | DOH by therapy area, value by warehouse, alert status pie, specialty vs non-specialty |
| **🚨 Reorder Alerts** | Scatter (DOH vs cost), full reorder table with supplier lead times |
| **🚚 Supplier Performance** | On-time rate bar, spend ranking, scorecard scatter |
| **💊 Prescriptions** | Monthly volume + fill rate overlay, therapy area fill rate, specialty comparison |
| **📉 Stockout Analysis** | Root cause pie, lost revenue bar, duration vs revenue scatter, detail table |

---

## 🔑 Key Technical Concepts

| Concept | Implementation |
|---|---|
| **Oracle-Compatible SQL** | ANSI standard SQL — runs on PostgreSQL and Oracle without modification |
| **Supply Chain ER Model** | 7 tables — suppliers, drugs, warehouses, inventory, POs, Rx, stockouts |
| **Days on Hand (DOH)** | `available_units / (avg_monthly_units/30)` — key pharmacy supply metric |
| **Inventory Reconciliation** | ETL validates `available = current - reserved`, auto-corrects mismatches |
| **Reorder Alert Logic** | Multi-tier alerts: OK → Low Stock → Reorder Now → Critical → Stockout |
| **Stored Function** | `fn_reorder_recommendation()` — returns prioritized reorder list per warehouse |
| **Database Views** | `vw_inventory_alerts` · `vw_supplier_scorecard` |
| **Window Functions** | Cumulative spend, MoM change, % of total spend |
| **Supplier Scorecard** | On-time rate, fill rate, avg delay, spend share per supplier |

---

## 📈 Sample KPIs

- **Inventory Value** — total $ value of available stock across all warehouses
- **Days on Hand (DOH)** — avg days of supply remaining at current dispensing rate
- **Prescription Fill Rate** — % of Rx successfully dispensed (~92%)
- **Supplier On-Time Rate** — % of POs received by expected date
- **Stockout Duration** — avg days a drug was out of stock
- **Lost Revenue** — $ revenue lost due to unfilled Rx during stockouts

---

## 🗃️ Dataset

- **20** suppliers (manufacturers + wholesale distributors)
- **25** drugs (specialty + non-specialty across 10 therapy areas)
- **5** regional warehouses
- **120** inventory records with DOH and reorder status
- **600** purchase orders with on-time tracking
- **8,000** prescriptions (2022–2024)
- **17** stockout events with root cause analysis

---

## 🔗 Related Projects

- [Specialty Pharmacy Claims Analytics](https://github.com/sumaksharikaa/sp-claims-analytics)
- [Drug Utilization & Formulary Analytics](https://github.com/sumaksharikaa/drug-utilization-analytics)
- [Healthcare Data Quality & Governance](https://github.com/sumaksharikaa/healthcare-dq-governance)
- [Pharmacy Readmission Risk Predictor](https://github.com/sumaksharikaa/pharmacy-readmission-risk)

---

*Built by [Sumaksharika Nainavarapu](https://sumaksharika.com) · B.S. Pharmacy · M.S. Health Informatics & Analytics*
