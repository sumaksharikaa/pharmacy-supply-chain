"""
app.py — Pharmacy Supply Chain & Prescription Analytics Dashboard
Run: streamlit run app/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Pharmacy Supply Chain Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

ALERT_COLORS = {
    "STOCKOUT": "#e74c3c", "CRITICAL": "#c0392b",
    "REORDER NOW": "#e67e22", "LOW STOCK": "#f1c40f",
    "OVERSTOCK": "#9b59b6", "HEALTHY": "#2ecc71", "OK": "#2ecc71"
}
GRADE_COLORS = {"A":"#2ecc71","B":"#27ae60","C":"#f39c12","D":"#e67e22","F":"#e74c3c"}
THERAPY_COLORS = px.colors.qualitative.Bold

@st.cache_data
def load_data():
    suppliers  = pd.read_csv(f"{DATA_DIR}/suppliers.csv")
    drugs      = pd.read_csv(f"{DATA_DIR}/drugs.csv")
    warehouses = pd.read_csv(f"{DATA_DIR}/warehouses.csv")
    inventory  = pd.read_csv(f"{DATA_DIR}/inventory.csv")
    po         = pd.read_csv(f"{DATA_DIR}/purchase_orders.csv", parse_dates=["order_date"])
    rx         = pd.read_csv(f"{DATA_DIR}/prescriptions.csv",   parse_dates=["rx_date"])
    stockouts  = pd.read_csv(f"{DATA_DIR}/stockout_events.csv", parse_dates=["start_date"])

    inv = (inventory
           .merge(drugs[["drug_id","brand_name","therapy_area","is_specialty","avg_monthly_units"]], on="drug_id")
           .merge(warehouses[["warehouse_id","warehouse_name","region","has_cold_storage"]], on="warehouse_id"))
    inv["alert_level"] = inv.apply(lambda r:
        "STOCKOUT"    if r["available_units"]==0    else
        "CRITICAL"    if r["is_stockout_risk"]      else
        "REORDER NOW" if r["is_below_reorder"]      else
        "OVERSTOCK"   if r["days_on_hand"]>90       else
        "HEALTHY", axis=1)

    rx  = rx.merge(drugs[["drug_id","brand_name","is_specialty"]], on="drug_id", how="left")
    po  = po.merge(suppliers[["supplier_id","supplier_name","performance_grade"]], on="supplier_id", how="left")
    po  = po.merge(drugs[["drug_id","brand_name","therapy_area"]], on="drug_id", how="left")
    rx["month"] = rx["rx_date"].dt.to_period("M").dt.to_timestamp()
    po["month"] = po["order_date"].dt.to_period("M").dt.to_timestamp()

    stockouts = stockouts.merge(drugs[["drug_id","brand_name","therapy_area"]], on="drug_id", how="left")
    return suppliers, drugs, warehouses, inv, po, rx, stockouts

suppliers, drugs, warehouses, inv, po, rx, stockouts = load_data()

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🏭 Supply Chain")
sel_specialty = st.sidebar.selectbox("Drug Type", ["All","Specialty Only","Non-Specialty Only"])
sel_therapy   = st.sidebar.multiselect("Therapy Area",
    sorted(inv["therapy_area"].unique()), default=sorted(inv["therapy_area"].unique()))
sel_region    = st.sidebar.multiselect("Warehouse Region",
    sorted(inv["region"].unique()), default=sorted(inv["region"].unique()))

finv = inv[inv["therapy_area"].isin(sel_therapy) & inv["region"].isin(sel_region)]
if sel_specialty == "Specialty Only":     finv = finv[finv["is_specialty"]==True]
elif sel_specialty == "Non-Specialty Only": finv = finv[finv["is_specialty"]==False]
frx  = rx[rx["therapy_area"].isin(sel_therapy)]

# ── header ────────────────────────────────────────────────────────────────────
st.title("🏭 Pharmacy Supply Chain & Prescription Analytics")
st.caption("Inventory management · Supplier performance · Prescription fill rates · Stockout analysis · Reorder alerts")
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1,k2,k3,k4,k5,k6 = st.columns(6)
inv_value   = (finv["available_units"] * finv["unit_cost_usd"]).sum()
fill_rate   = frx["is_filled"].mean()*100
below_reord = finv["is_below_reorder"].sum()
stockout_r  = finv["is_stockout_risk"].sum()
avg_doh     = finv["days_on_hand"].mean()
lost_rev    = stockouts["lost_revenue_usd"].sum()

k1.metric("Inventory Value",     f"${inv_value/1e6:.2f}M")
k2.metric("Avg Days on Hand",    f"{avg_doh:.1f}")
k3.metric("Rx Fill Rate",        f"{fill_rate:.1f}%")
k4.metric("Below Reorder Point", f"{below_reord}")
k5.metric("Stockout Risk SKUs",  f"{stockout_r}")
k6.metric("Lost Revenue",        f"${lost_rev:,.0f}")
st.divider()

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "📦 Inventory","🚨 Reorder Alerts","🚚 Supplier Performance",
    "💊 Prescriptions","📉 Stockout Analysis"
])

# ══ TAB 1 — INVENTORY ════════════════════════════════════════════════════════
with tab1:
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Days on Hand by Therapy Area")
        doh_therapy = (finv.groupby("therapy_area")
                       .agg(avg_doh=("days_on_hand","mean"),
                            min_doh=("days_on_hand","min"),
                            skus=("drug_id","nunique"))
                       .reset_index().sort_values("avg_doh"))
        fig = px.bar(doh_therapy, x="avg_doh", y="therapy_area", orientation="h",
                     color="avg_doh",
                     color_continuous_scale=["#e74c3c","#f39c12","#2ecc71"],
                     text=doh_therapy["avg_doh"].round(1),
                     labels={"avg_doh":"Avg Days on Hand","therapy_area":"Therapy Area"})
        fig.add_vline(x=30, line_dash="dash", line_color="#e74c3c",
                      annotation_text="30-day threshold")
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Inventory Value by Warehouse")
        wh_val = (finv.groupby(["warehouse_name","region"])
                  .apply(lambda x: (x["available_units"]*x["unit_cost_usd"]).sum())
                  .reset_index(name="value").sort_values("value", ascending=False))
        fig2 = px.bar(wh_val, x="warehouse_name", y="value",
                      color="region", color_discrete_sequence=THERAPY_COLORS,
                      labels={"value":"Inventory Value ($)","warehouse_name":"Warehouse"})
        fig2.update_layout(xaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Alert Status Distribution")
    c1,c2 = st.columns(2)
    with c1:
        alert_cnt = finv["alert_level"].value_counts().reset_index()
        alert_cnt.columns = ["Alert","Count"]
        fig3 = px.pie(alert_cnt, values="Count", names="Alert", hole=0.45,
                      color="Alert", color_discrete_map=ALERT_COLORS)
        st.plotly_chart(fig3, use_container_width=True)
    with c2:
        st.subheader("Inventory by Specialty Type")
        spec = (finv.groupby("is_specialty")
                .apply(lambda x: (x["available_units"]*x["unit_cost_usd"]).sum())
                .reset_index(name="value"))
        spec["type"] = spec["is_specialty"].map({True:"Specialty",False:"Non-Specialty"})
        fig4 = px.pie(spec, values="value", names="type", hole=0.45,
                      color_discrete_sequence=["#e74c3c","#3498db"])
        st.plotly_chart(fig4, use_container_width=True)

# ══ TAB 2 — REORDER ALERTS ═══════════════════════════════════════════════════
with tab2:
    st.subheader("🚨 Reorder Alert Dashboard")
    alerts = finv[finv["is_below_reorder"]==True].copy()
    alerts = alerts.merge(
        drugs[["drug_id","primary_supplier_id","avg_monthly_units","unit_cost_usd"]],
        on="drug_id", suffixes=("","_drug"))
    alerts = alerts.merge(
        suppliers[["supplier_id","supplier_name","lead_time_days","performance_grade"]],
        left_on="primary_supplier_id", right_on="supplier_id", how="left")
    alerts["recommended_qty"] = alerts["avg_monthly_units"] * 2
    alerts["estimated_cost"]  = (alerts["recommended_qty"] * alerts["unit_cost_usd_drug"]).round(2)

    c1,c2,c3 = st.columns(3)
    c1.metric("SKUs Below Reorder",  len(alerts))
    c2.metric("Estimated PO Value",  f"${alerts['estimated_cost'].sum():,.0f}")
    c3.metric("Critical (0 stock)",  (alerts["available_units"]==0).sum())

    fig = px.scatter(alerts, x="days_on_hand", y="estimated_cost",
                     size="recommended_qty", color="alert_level",
                     color_discrete_map=ALERT_COLORS,
                     hover_data=["brand_name","warehouse_name","supplier_name"],
                     text="brand_name",
                     labels={"days_on_hand":"Days on Hand","estimated_cost":"Est. PO Cost ($)"})
    fig.update_traces(textposition="top center")
    fig.add_vline(x=15, line_dash="dash", line_color="#e74c3c")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        alerts[["brand_name","therapy_area","warehouse_name","available_units",
                "days_on_hand","alert_level","supplier_name","lead_time_days",
                "performance_grade","recommended_qty","estimated_cost"]]
        .sort_values("days_on_hand")
        .rename(columns={"brand_name":"Drug","therapy_area":"Therapy",
                          "warehouse_name":"Warehouse","available_units":"Available",
                          "days_on_hand":"DOH","alert_level":"Alert",
                          "supplier_name":"Supplier","lead_time_days":"Lead Days",
                          "performance_grade":"Grade","recommended_qty":"Rec. Qty",
                          "estimated_cost":"Est. Cost ($)"}),
        use_container_width=True, hide_index=True
    )

# ══ TAB 3 — SUPPLIER PERFORMANCE ═════════════════════════════════════════════
with tab3:
    sup_perf = (po.groupby(["supplier_id","supplier_name","performance_grade"])
                .agg(total_orders=("po_id","count"),
                     total_spend=("total_cost_usd","sum"),
                     on_time=("on_time_delivery","sum"),
                     avg_delay=("delay_days","mean"),
                     avg_lead=("delay_days",lambda x: x.count()))
                .reset_index())
    sup_perf["on_time_pct"] = (sup_perf["on_time"] / sup_perf["total_orders"] * 100).round(1)
    sup_perf = sup_perf.merge(suppliers[["supplier_id","lead_time_days","supplier_type"]], on="supplier_id")

    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Supplier On-Time Delivery Rate")
        fig = px.bar(sup_perf.sort_values("on_time_pct"), x="on_time_pct", y="supplier_name",
                     orientation="h", color="performance_grade",
                     color_discrete_map=GRADE_COLORS,
                     text=sup_perf.sort_values("on_time_pct")["on_time_pct"].apply(lambda x: f"{x:.1f}%"),
                     labels={"on_time_pct":"On-Time %","supplier_name":"Supplier"})
        fig.add_vline(x=90, line_dash="dash", line_color="#2c3e50",
                      annotation_text="90% target")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Total Spend by Supplier")
        fig2 = px.bar(sup_perf.sort_values("total_spend",ascending=False).head(10),
                      x="total_spend", y="supplier_name", orientation="h",
                      color="performance_grade", color_discrete_map=GRADE_COLORS,
                      labels={"total_spend":"Total Spend ($)","supplier_name":"Supplier"})
        fig2.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Supplier Scorecard — On-Time % vs Spend")
    fig3 = px.scatter(sup_perf, x="total_spend", y="on_time_pct",
                      size="total_orders", color="performance_grade",
                      color_discrete_map=GRADE_COLORS,
                      text="supplier_name",
                      labels={"total_spend":"Total Spend ($)",
                               "on_time_pct":"On-Time Rate (%)","performance_grade":"Grade"})
    fig3.add_hline(y=90, line_dash="dash", line_color="#2c3e50")
    fig3.update_traces(textposition="top center")
    st.plotly_chart(fig3, use_container_width=True)

# ══ TAB 4 — PRESCRIPTIONS ════════════════════════════════════════════════════
with tab4:
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Monthly Rx Volume & Fill Rate")
        monthly = (frx.groupby("month")
                   .agg(total=("rx_id","count"), filled=("is_filled","sum"),
                        spend=("total_cost_usd","sum")).reset_index())
        monthly["fill_rate"] = (monthly["filled"]/monthly["total"]*100).round(1)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["month"], y=monthly["total"],
                             name="Total Rx", marker_color="#aed6f1"))
        fig.add_trace(go.Bar(x=monthly["month"], y=monthly["filled"],
                             name="Filled Rx", marker_color="#2980b9"))
        fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["fill_rate"],
                                 name="Fill Rate %", yaxis="y2",
                                 line=dict(color="#e74c3c", width=2)))
        fig.update_layout(barmode="overlay", yaxis2=dict(overlaying="y",side="right",
                          title="Fill Rate %", range=[80,100]),
                          legend=dict(x=0,y=1), xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Fill Rate by Therapy Area")
        therapy_fill = (frx.groupby("therapy_area")
                        .agg(total=("rx_id","count"), filled=("is_filled","sum"))
                        .reset_index())
        therapy_fill["fill_rate"] = (therapy_fill["filled"]/therapy_fill["total"]*100).round(1)
        therapy_fill = therapy_fill.sort_values("fill_rate")
        fig2 = px.bar(therapy_fill, x="fill_rate", y="therapy_area", orientation="h",
                      color="fill_rate",
                      color_continuous_scale=["#e74c3c","#f39c12","#2ecc71"],
                      text=therapy_fill["fill_rate"].apply(lambda x: f"{x:.1f}%"),
                      labels={"fill_rate":"Fill Rate (%)","therapy_area":"Therapy"})
        fig2.add_vline(x=92, line_dash="dash", line_color="#2c3e50")
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Specialty vs Non-Specialty Prescription Analysis")
    spec_rx = (frx.groupby("is_specialty")
               .agg(total=("rx_id","count"), filled=("is_filled","sum"),
                    spend=("total_cost_usd","sum"),
                    avg_cost=("total_cost_usd","mean")).reset_index())
    spec_rx["type"] = spec_rx["is_specialty"].map({True:"Specialty",False:"Non-Specialty"})
    spec_rx["fill_rate"] = (spec_rx["filled"]/spec_rx["total"]*100).round(1)
    c1,c2,c3,c4 = st.columns(4)
    for col,(_, row) in zip([c1,c2,c3,c4], spec_rx.iterrows()):
        col.metric(f"{row['type']} Fill Rate", f"{row['fill_rate']:.1f}%")
        col.metric(f"{row['type']} Avg Cost",  f"${row['avg_cost']:,.0f}")

# ══ TAB 5 — STOCKOUT ANALYSIS ════════════════════════════════════════════════
with tab5:
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Stockout Root Causes")
        rc = stockouts["root_cause"].value_counts().reset_index()
        rc.columns = ["Root Cause","Count"]
        fig = px.pie(rc, values="Count", names="Root Cause", hole=0.45,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Lost Revenue by Root Cause")
        rev = (stockouts.groupby("root_cause")["lost_revenue_usd"]
               .sum().reset_index().sort_values("lost_revenue_usd",ascending=False))
        fig2 = px.bar(rev, x="lost_revenue_usd", y="root_cause", orientation="h",
                      color_discrete_sequence=["#e74c3c"],
                      labels={"lost_revenue_usd":"Lost Revenue ($)","root_cause":"Root Cause"})
        fig2.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Stockout Events — Duration vs Lost Revenue")
    fig3 = px.scatter(stockouts, x="duration_days", y="lost_revenue_usd",
                      size="lost_rx_count", color="root_cause",
                      hover_data=["brand_name","therapy_area"],
                      labels={"duration_days":"Duration (Days)",
                               "lost_revenue_usd":"Lost Revenue ($)","root_cause":"Root Cause"})
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Stockout Detail Table")
    st.dataframe(
        stockouts[["stockout_id","brand_name","therapy_area","warehouse_id",
                   "start_date","duration_days","lost_rx_count","lost_revenue_usd","root_cause","resolved"]]
        .rename(columns={"stockout_id":"ID","brand_name":"Drug","therapy_area":"Therapy",
                          "warehouse_id":"Warehouse","start_date":"Start","duration_days":"Days",
                          "lost_rx_count":"Lost Rx","lost_revenue_usd":"Lost Rev ($)",
                          "root_cause":"Root Cause","resolved":"Resolved"}),
        use_container_width=True, hide_index=True
    )

st.divider()
st.caption("Pharmacy Supply Chain & Prescription Analytics · PostgreSQL · Python ETL · Streamlit · Oracle-compatible SQL · sumaksharika.com")
