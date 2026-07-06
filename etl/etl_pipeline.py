"""
etl_pipeline.py
Pharmacy Supply Chain & Prescription Analytics — ETL Pipeline
Extract → Validate → Transform → Load into PostgreSQL
Oracle-compatible SQL used throughout
"""

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
import logging, os, sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("etl.log")]
)
log = logging.getLogger(__name__)

DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "pharmacy_sc_db"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

VALID_GRADES  = {"A","B","C","D","F"}
VALID_STATUSES= {"Pending","Received","Cancelled","Partial"}


class SupplyChainETL:
    def __init__(self):
        self.conn  = None
        self.cur   = None
        self.stats = {}
        self.dq    = []

    def connect(self):
        log.info("Connecting to PostgreSQL...")
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur  = self.conn.cursor()
        log.info("Connected ✓")

    def disconnect(self):
        if self.cur:  self.cur.close()
        if self.conn: self.conn.close()

    def extract(self, filename):
        path = os.path.join(DATA_DIR, filename)
        log.info(f"Extracting {filename}...")
        df = pd.read_csv(path, low_memory=False)
        log.info(f"  → {len(df):,} rows")
        return df

    def _flag(self, df, pk, cond, label):
        n = int(cond.sum())
        if n:
            log.warning(f"  ⚠ {label}: {n} rows")
            self.dq.append({"check": label, "issues": n})
        return df[~cond].copy()

    # ── transforms ────────────────────────────────────────────────────────────
    def transform_suppliers(self, df):
        log.info("Transforming suppliers...")
        df = df.drop_duplicates("supplier_id")
        df["contract_start"] = pd.to_datetime(df["contract_start"]).dt.date
        df["on_time_rate"]   = pd.to_numeric(df["on_time_rate"], errors="coerce").clip(0,1)
        df["fill_rate"]      = pd.to_numeric(df["fill_rate"],    errors="coerce").clip(0,1)
        df["is_preferred"]   = df["is_preferred"].astype(bool)
        df = self._flag(df,"supplier_id", ~df["performance_grade"].isin(VALID_GRADES),
                        "suppliers: invalid grade")
        return df

    def transform_drugs(self, df):
        log.info("Transforming drugs...")
        df = df.drop_duplicates("drug_id")
        df["unit_cost_usd"]     = pd.to_numeric(df["unit_cost_usd"], errors="coerce")
        df["is_specialty"]      = df["is_specialty"].astype(bool)
        df["requires_cold_chain"]= df["requires_cold_chain"].astype(bool)
        df = self._flag(df,"drug_id", df["unit_cost_usd"]<=0, "drugs: invalid cost")
        return df

    def transform_warehouses(self, df):
        log.info("Transforming warehouses...")
        df = df.drop_duplicates("warehouse_id")
        df["has_cold_storage"] = df["has_cold_storage"].astype(bool)
        return df

    def transform_inventory(self, df):
        log.info("Transforming inventory...")
        df = df.drop_duplicates(["drug_id","warehouse_id"])
        for col in ["current_units","reserved_units","available_units"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        df["last_updated"]     = pd.to_datetime(df["last_updated"]).dt.date
        df["expiry_date"]      = pd.to_datetime(df["expiry_date"], errors="coerce").dt.date
        df["days_on_hand"]     = pd.to_numeric(df["days_on_hand"], errors="coerce").fillna(0)
        df["is_below_reorder"] = df["is_below_reorder"].astype(bool)
        df["is_stockout_risk"] = df["is_stockout_risk"].astype(bool)
        df = self._flag(df,"inventory_id", df["available_units"]<0, "inventory: negative units")

        # Reconciliation: available = current - reserved
        calc = df["current_units"] - df["reserved_units"]
        mismatch = (abs(calc - df["available_units"]) > 0).sum()
        if mismatch:
            log.warning(f"  ⚠ Reconciliation: {mismatch} available_units corrected")
            df["available_units"] = calc.clip(lower=0)
        return df

    def transform_purchase_orders(self, df):
        log.info("Transforming purchase orders...")
        df = df.drop_duplicates("po_id")
        df["order_date"]          = pd.to_datetime(df["order_date"]).dt.date
        df["expected_date"]       = pd.to_datetime(df["expected_date"]).dt.date
        df["actual_receipt_date"] = pd.to_datetime(df["actual_receipt_date"], errors="coerce").dt.date
        df["total_cost_usd"]      = pd.to_numeric(df["total_cost_usd"], errors="coerce").fillna(0)
        df["unit_cost_usd"]       = pd.to_numeric(df["unit_cost_usd"], errors="coerce").fillna(0)
        df["on_time_delivery"]    = df["on_time_delivery"].astype(bool)
        df["delay_days"]          = pd.to_numeric(df["delay_days"], errors="coerce").fillna(0).astype(int)
        df = self._flag(df,"po_id", ~df["status"].isin(VALID_STATUSES), "PO: invalid status")
        return df

    def transform_prescriptions(self, df):
        log.info("Transforming prescriptions...")
        df = df.drop_duplicates("rx_id")
        df["rx_date"]           = pd.to_datetime(df["rx_date"]).dt.date
        df["fill_date"]         = pd.to_datetime(df["fill_date"], errors="coerce").dt.date
        df["days_to_fill"]      = pd.to_numeric(df["days_to_fill"], errors="coerce")
        df["quantity_dispensed"]= pd.to_numeric(df["quantity_dispensed"], errors="coerce").fillna(0).astype(int)
        df["total_cost_usd"]    = pd.to_numeric(df["total_cost_usd"], errors="coerce").fillna(0)
        df["is_filled"]         = df["is_filled"].astype(bool)
        df["is_specialty"]      = df["is_specialty"].astype(bool)
        df["refill_number"]     = pd.to_numeric(df["refill_number"], errors="coerce").fillna(0).astype(int)
        df["days_supply"]       = pd.to_numeric(df["days_supply"], errors="coerce").fillna(30).astype(int)
        log.info(f"  Fill rate: {df['is_filled'].mean()*100:.1f}%")
        return df

    def transform_stockouts(self, df):
        log.info("Transforming stockout events...")
        df = df.drop_duplicates("stockout_id")
        df["start_date"]       = pd.to_datetime(df["start_date"]).dt.date
        df["end_date"]         = pd.to_datetime(df["end_date"]).dt.date
        df["duration_days"]    = pd.to_numeric(df["duration_days"], errors="coerce").fillna(0).astype(int)
        df["lost_revenue_usd"] = pd.to_numeric(df["lost_revenue_usd"], errors="coerce").fillna(0)
        df["resolved"]         = df["resolved"].astype(bool)
        return df

    # ── load ──────────────────────────────────────────────────────────────────
    def _load(self, table, df, cols, pk):
        if df.empty: return 0
        rows = [tuple(None if pd.isna(v) else v for v in r)
                for r in df[cols].itertuples(index=False)]
        ph  = ",".join(["%s"]*len(cols))
        upd = ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c != pk)
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT ({pk}) DO UPDATE SET {upd}"
        execute_values(self.cur, sql, rows)
        self.conn.commit()
        log.info(f"  ✓ {table}: {len(rows):,} rows loaded")
        self.stats[table] = len(rows)
        return len(rows)

    def run(self):
        start = datetime.now()
        log.info("="*55)
        log.info("PHARMACY SUPPLY CHAIN ETL — STARTING")
        log.info("="*55)
        try:
            self.connect()
            self._load("suppliers", self.transform_suppliers(self.extract("suppliers.csv")),
                ["supplier_id","supplier_name","supplier_type","state","performance_grade",
                 "lead_time_days","on_time_rate","fill_rate","contract_start","is_preferred"], "supplier_id")
            self._load("warehouses", self.transform_warehouses(self.extract("warehouses.csv")),
                ["warehouse_id","warehouse_name","city","state","region",
                 "has_cold_storage","capacity_units"], "warehouse_id")
            self._load("drugs", self.transform_drugs(self.extract("drugs.csv")),
                ["drug_id","brand_name","generic_name","primary_supplier_id","therapy_area",
                 "dosage_form","strength","ndc","unit_cost_usd","is_specialty",
                 "requires_cold_chain","days_supply_std","avg_monthly_units",
                 "reorder_point_units","safety_stock_units"], "drug_id")
            self._load("inventory", self.transform_inventory(self.extract("inventory.csv")),
                ["inventory_id","drug_id","warehouse_id","current_units","reserved_units",
                 "available_units","unit_cost_usd","reorder_point","safety_stock",
                 "days_on_hand","is_below_reorder","is_stockout_risk",
                 "expiry_date","last_updated"], "inventory_id")
            self._load("purchase_orders", self.transform_purchase_orders(self.extract("purchase_orders.csv")),
                ["po_id","supplier_id","warehouse_id","drug_id","order_date","expected_date",
                 "actual_receipt_date","status","on_time_delivery","delay_days",
                 "total_units","unit_cost_usd","total_cost_usd"], "po_id")
            self._load("prescriptions", self.transform_prescriptions(self.extract("prescriptions.csv")),
                ["rx_id","patient_id","drug_id","warehouse_id","rx_date","fill_date",
                 "days_to_fill","quantity_dispensed","days_supply","is_filled","fill_status",
                 "unit_cost_usd","total_cost_usd","is_specialty","therapy_area","refill_number"], "rx_id")
            self._load("stockout_events", self.transform_stockouts(self.extract("stockout_events.csv")),
                ["stockout_id","drug_id","warehouse_id","start_date","end_date",
                 "duration_days","lost_rx_count","lost_revenue_usd","root_cause","resolved"], "stockout_id")
        except Exception as e:
            log.error(f"ETL failed: {e}")
            if self.conn: self.conn.rollback()
            raise
        finally:
            self.disconnect()
        elapsed = (datetime.now()-start).seconds
        log.info(f"\nETL COMPLETE in {elapsed}s | Rows: {self.stats}")
        if self.dq: log.warning(f"DQ issues: {self.dq}")


if __name__ == "__main__":
    SupplyChainETL().run()
