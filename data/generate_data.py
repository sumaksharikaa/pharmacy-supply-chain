"""
generate_data.py
Pharmacy Supply Chain & Prescription Analytics — Data Generator
Tables: suppliers, drugs, warehouses, inventory, purchase_orders,
        purchase_order_lines, prescriptions, distribution_events, stockout_events
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

random.seed(55)
np.random.seed(55)

OUT = os.path.dirname(__file__)
START = datetime(2022, 1, 1)
END   = datetime(2024, 12, 31)

def rdate(s=START, e=END):
    return s + timedelta(days=random.randint(0, (e - s).days))
def fmt(d): return d.strftime("%Y-%m-%d")

# ── suppliers (20) ────────────────────────────────────────────────────────────
SUPPLIERS = [
    ("SUP001","AmerisourceBergen","Wholesale Distributor","PA","A"),
    ("SUP002","McKesson Corporation","Wholesale Distributor","TX","A"),
    ("SUP003","Cardinal Health","Wholesale Distributor","OH","A"),
    ("SUP004","AbbVie Inc","Manufacturer","IL","A"),
    ("SUP005","Pfizer Inc","Manufacturer","NY","A"),
    ("SUP006","Merck & Co","Manufacturer","NJ","A"),
    ("SUP007","Novo Nordisk","Manufacturer","NJ","B"),
    ("SUP008","Janssen Pharmaceuticals","Manufacturer","PA","A"),
    ("SUP009","Biogen Inc","Manufacturer","MA","B"),
    ("SUP010","Gilead Sciences","Manufacturer","CA","A"),
    ("SUP011","AstraZeneca","Manufacturer","DE","A"),
    ("SUP012","Sanofi","Manufacturer","NJ","B"),
    ("SUP013","Amgen Inc","Manufacturer","CA","A"),
    ("SUP014","BMS","Manufacturer","NY","A"),
    ("SUP015","Generic Pharma Co","Generic Manufacturer","NJ","C"),
    ("SUP016","Teva Pharmaceuticals","Generic Manufacturer","PA","B"),
    ("SUP017","Mylan Pharmaceuticals","Generic Manufacturer","PA","C"),
    ("SUP018","Sandoz","Generic Manufacturer","NJ","B"),
    ("SUP019","Actavis","Generic Manufacturer","NJ","C"),
    ("SUP020","Sun Pharma","Generic Manufacturer","NJ","C"),
]
suppliers_df = pd.DataFrame(SUPPLIERS,
    columns=["supplier_id","supplier_name","supplier_type","state","performance_grade"])
suppliers_df["lead_time_days"]     = np.where(suppliers_df["supplier_type"]=="Manufacturer",
                                               np.random.randint(14,45,20), np.random.randint(3,10,20))
suppliers_df["on_time_rate"]       = np.where(suppliers_df["performance_grade"]=="A",
                                               np.random.uniform(0.90,0.99,20),
                                               np.where(suppliers_df["performance_grade"]=="B",
                                               np.random.uniform(0.75,0.90,20),
                                               np.random.uniform(0.60,0.75,20))).round(3)
suppliers_df["fill_rate"]          = (suppliers_df["on_time_rate"] * np.random.uniform(0.95,1.0,20)).round(3)
suppliers_df["contract_start"]     = "2022-01-01"
suppliers_df["is_preferred"]       = suppliers_df["performance_grade"].isin(["A"])
suppliers_df.to_csv(f"{OUT}/suppliers.csv", index=False)

# ── drugs (25) ────────────────────────────────────────────────────────────────
DRUGS = [
    ("DRG001","Humira","Adalimumab","SUP004","Immunology","Injection","40mg",6500,True,True,30,5),
    ("DRG002","Enbrel","Etanercept","SUP005","Immunology","Injection","50mg",5800,True,True,30,5),
    ("DRG003","Stelara","Ustekinumab","SUP008","Dermatology","Injection","45mg",18000,True,True,20,3),
    ("DRG004","Keytruda","Pembrolizumab","SUP006","Oncology","Injection","200mg",22000,True,True,15,2),
    ("DRG005","Revlimid","Lenalidomide","SUP014","Oncology","Capsule","25mg",19000,True,False,20,3),
    ("DRG006","Ozempic","Semaglutide","SUP007","Diabetes","Injection","1mg",850,True,False,60,10),
    ("DRG007","Dupixent","Dupilumab","SUP012","Dermatology","Injection","300mg",3200,True,True,30,5),
    ("DRG008","Tecfidera","Dimethyl Fumarate","SUP009","Neurology","Capsule","240mg",8100,True,False,30,5),
    ("DRG009","Harvoni","Ledipasvir","SUP010","Hepatology","Tablet","90mg",31000,True,False,15,2),
    ("DRG010","Truvada","Emtricitabine","SUP010","Infectious Disease","Tablet","200mg",2700,False,False,90,15),
    ("DRG011","Lipitor","Atorvastatin","SUP005","Cardiology","Tablet","20mg",12,False,False,90,200),
    ("DRG012","Metformin","Metformin HCl","SUP015","Diabetes","Tablet","500mg",4,False,False,90,500),
    ("DRG013","Lisinopril","Lisinopril","SUP016","Cardiology","Tablet","10mg",3,False,False,90,600),
    ("DRG014","Amlodipine","Amlodipine","SUP017","Cardiology","Tablet","5mg",4,False,False,90,550),
    ("DRG015","Omeprazole","Omeprazole","SUP018","Gastroenterology","Capsule","20mg",6,False,False,90,400),
    ("DRG016","Eliquis","Apixaban","SUP014","Cardiology","Tablet","5mg",145,False,False,90,100),
    ("DRG017","Xarelto","Rivaroxaban","SUP008","Cardiology","Tablet","20mg",140,False,False,90,95),
    ("DRG018","Januvia","Sitagliptin","SUP006","Diabetes","Tablet","100mg",85,False,False,90,80),
    ("DRG019","Advair","Fluticasone/Salm","SUP011","Pulmonology","Inhaler","250mcg",95,False,False,30,60),
    ("DRG020","Crestor","Rosuvastatin","SUP011","Cardiology","Tablet","10mg",18,False,False,90,180),
    ("DRG021","Gabapentin","Gabapentin","SUP019","Neurology","Capsule","300mg",8,False,False,90,300),
    ("DRG022","Sertraline","Sertraline HCl","SUP020","Psychiatry","Tablet","50mg",5,False,False,90,350),
    ("DRG023","Levothyroxine","Levothyroxine","SUP015","Endocrinology","Tablet","50mcg",4,False,False,90,450),
    ("DRG024","Warfarin","Warfarin Sodium","SUP016","Cardiology","Tablet","5mg",6,False,False,30,120),
    ("DRG025","Furosemide","Furosemide","SUP017","Cardiology","Tablet","40mg",3,False,False,30,200),
]
drug_cols = ["drug_id","brand_name","generic_name","primary_supplier_id","therapy_area",
             "dosage_form","strength","unit_cost_usd","is_specialty","requires_cold_chain",
             "days_supply_std","avg_monthly_units"]
drugs_df = pd.DataFrame(DRUGS, columns=drug_cols)
drugs_df["ndc"] = [f"{random.randint(10000,99999)}-{random.randint(100,999)}-{random.randint(10,99)}" for _ in range(len(drugs_df))]
drugs_df["reorder_point_units"] = (drugs_df["avg_monthly_units"] * 0.5).astype(int)
drugs_df["safety_stock_units"]  = (drugs_df["avg_monthly_units"] * 0.25).astype(int)
drugs_df.to_csv(f"{OUT}/drugs.csv", index=False)

# ── warehouses (5) ────────────────────────────────────────────────────────────
warehouses = pd.DataFrame([
    ("WH001","Charlotte DC","Charlotte","NC","Southeast",True),
    ("WH002","Dallas DC","Dallas","TX","South Central",True),
    ("WH003","Los Angeles DC","Los Angeles","CA","West",True),
    ("WH004","Chicago DC","Chicago","IL","Midwest",False),
    ("WH005","New York DC","New York","NY","Northeast",True),
], columns=["warehouse_id","warehouse_name","city","state","region","has_cold_storage"])
warehouses["capacity_units"] = [50000,45000,48000,42000,47000]
warehouses.to_csv(f"{OUT}/warehouses.csv", index=False)

# ── inventory (current stock per drug per warehouse) ──────────────────────────
inv_records = []
for _, drug in drugs_df.iterrows():
    for _, wh in warehouses.iterrows():
        if drug["requires_cold_chain"] and not wh["has_cold_storage"]:
            continue
        base_units = drug["avg_monthly_units"]
        curr_units = max(0, int(np.random.normal(base_units * 1.5, base_units * 0.3)))
        inv_records.append({
            "inventory_id":       f"INV{len(inv_records)+1:06d}",
            "drug_id":            drug["drug_id"],
            "warehouse_id":       wh["warehouse_id"],
            "current_units":      curr_units,
            "reserved_units":     int(curr_units * random.uniform(0.05, 0.15)),
            "available_units":    0,  # computed below
            "unit_cost_usd":      drug["unit_cost_usd"],
            "reorder_point":      drug["reorder_point_units"],
            "safety_stock":       drug["safety_stock_units"],
            "last_updated":       fmt(END),
            "expiry_date":        fmt(END + timedelta(days=random.randint(90,730))),
            "days_on_hand":       0,  # computed below
        })

inv_df = pd.DataFrame(inv_records)
inv_df["available_units"] = inv_df["current_units"] - inv_df["reserved_units"]
inv_df = inv_df.merge(drugs_df[["drug_id","avg_monthly_units"]], on="drug_id")
inv_df["days_on_hand"] = ((inv_df["available_units"] / (inv_df["avg_monthly_units"]/30)).round(1))
inv_df["is_below_reorder"] = inv_df["available_units"] < inv_df["reorder_point"]
inv_df["is_stockout_risk"] = inv_df["available_units"] < inv_df["safety_stock"]
inv_df = inv_df.drop(columns=["avg_monthly_units"])
inv_df.to_csv(f"{OUT}/inventory.csv", index=False)

# ── purchase orders (600) ─────────────────────────────────────────────────────
po_records = []
for i in range(1, 601):
    drug    = drugs_df.sample(1).iloc[0]
    sup_id  = drug["primary_supplier_id"]
    sup     = suppliers_df[suppliers_df["supplier_id"]==sup_id].iloc[0]
    wh      = warehouses.sample(1).iloc[0]
    ord_d   = rdate()
    lead    = int(sup["lead_time_days"])
    exp_d   = ord_d + timedelta(days=lead)
    on_time = random.random() < sup["on_time_rate"]
    delay   = 0 if on_time else random.randint(1, 10)
    act_d   = exp_d + timedelta(days=delay) if random.random()>0.05 else None
    qty     = int(drug["avg_monthly_units"] * random.uniform(1, 4))
    unit_c  = round(drug["unit_cost_usd"] * random.uniform(0.90, 1.00), 2)
    po_records.append({
        "po_id":              f"PO{i:06d}",
        "supplier_id":        sup_id,
        "warehouse_id":       wh["warehouse_id"],
        "order_date":         fmt(ord_d),
        "expected_date":      fmt(exp_d),
        "actual_receipt_date":fmt(act_d) if act_d else None,
        "status":             "Received" if act_d else "Pending",
        "on_time_delivery":   on_time,
        "delay_days":         delay,
        "total_units":        qty,
        "unit_cost_usd":      unit_c,
        "total_cost_usd":     round(qty * unit_c, 2),
        "drug_id":            drug["drug_id"],
    })

po_df = pd.DataFrame(po_records)
po_df.to_csv(f"{OUT}/purchase_orders.csv", index=False)

# ── prescriptions (8000) ─────────────────────────────────────────────────────
rx_records = []
patient_ids = [f"PT{i:06d}" for i in range(1, 2001)]
for i in range(1, 8001):
    drug     = drugs_df.sample(1).iloc[0]
    wh       = warehouses.sample(1).iloc[0]
    svc_d    = rdate()
    qty      = random.randint(1, 3)
    cost     = round(drug["unit_cost_usd"] * qty * random.uniform(0.95, 1.05), 2)
    filled   = random.random() > 0.08  # 92% fill rate
    days_to  = random.randint(0, 3) if filled else None
    rx_records.append({
        "rx_id":              f"RX{i:07d}",
        "patient_id":         random.choice(patient_ids),
        "drug_id":            drug["drug_id"],
        "warehouse_id":       wh["warehouse_id"],
        "rx_date":            fmt(svc_d),
        "fill_date":          fmt(svc_d + timedelta(days=days_to)) if days_to is not None else None,
        "days_to_fill":       days_to,
        "quantity_dispensed": qty if filled else 0,
        "days_supply":        drug["days_supply_std"],
        "is_filled":          filled,
        "fill_status":        "Filled" if filled else "Unfilled — Out of Stock",
        "unit_cost_usd":      drug["unit_cost_usd"],
        "total_cost_usd":     cost if filled else 0,
        "is_specialty":       drug["is_specialty"],
        "therapy_area":       drug["therapy_area"],
        "refill_number":      random.randint(0, 5),
    })

rx_df = pd.DataFrame(rx_records)
rx_df.to_csv(f"{OUT}/prescriptions.csv", index=False)

# ── stockout events ───────────────────────────────────────────────────────────
stockout_records = []
low_inv = inv_df[inv_df["is_stockout_risk"]==True]
for i, (_, row) in enumerate(low_inv.iterrows(), 1):
    start_d = rdate(datetime(2024,6,1), END)
    dur     = random.randint(1, 14)
    end_d   = start_d + timedelta(days=dur)
    drug    = drugs_df[drugs_df["drug_id"]==row["drug_id"]].iloc[0]
    stockout_records.append({
        "stockout_id":        f"STK{i:05d}",
        "drug_id":            row["drug_id"],
        "warehouse_id":       row["warehouse_id"],
        "start_date":         fmt(start_d),
        "end_date":           fmt(end_d),
        "duration_days":      dur,
        "lost_rx_count":      random.randint(1, 20),
        "lost_revenue_usd":   round(random.randint(1,20) * drug["unit_cost_usd"], 2),
        "root_cause":         random.choice(["Supplier delay","Demand spike",
                                              "Forecast error","Cold chain failure",
                                              "Regulatory hold"]),
        "resolved":           True,
    })

stockout_df = pd.DataFrame(stockout_records)
stockout_df.to_csv(f"{OUT}/stockout_events.csv", index=False)

print("✅ Generated:")
for name, df in [("suppliers",suppliers_df),("drugs",drugs_df),("warehouses",warehouses),
                 ("inventory",inv_df),("purchase_orders",po_df),
                 ("prescriptions",rx_df),("stockout_events",stockout_df)]:
    print(f"   {name+'.csv':<25} → {len(df):,} rows")
