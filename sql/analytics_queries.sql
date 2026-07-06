-- =============================================================================
-- analytics_queries.sql
-- Pharmacy Supply Chain & Prescription Analytics — KPI Queries
-- Oracle-compatible SQL (ANSI standard, works on PostgreSQL and Oracle)
-- =============================================================================

-- =============================================================================
-- 1. EXECUTIVE SUMMARY — Inventory, Spend, Fill Rate
-- =============================================================================
SELECT
    COUNT(DISTINCT d.drug_id)                           AS total_skus,
    COUNT(DISTINCT d.drug_id) FILTER
        (WHERE d.is_specialty = TRUE)                   AS specialty_skus,
    ROUND(SUM(i.available_units * i.unit_cost_usd), 2) AS total_inventory_value_usd,
    ROUND(AVG(i.days_on_hand), 1)                       AS avg_days_on_hand,
    COUNT(*) FILTER (WHERE i.is_below_reorder = TRUE)   AS skus_below_reorder,
    COUNT(*) FILTER (WHERE i.is_stockout_risk = TRUE)   AS skus_at_stockout_risk,
    ROUND(COUNT(*) FILTER (WHERE i.is_below_reorder)
        * 100.0 / COUNT(*), 2)                          AS pct_below_reorder
FROM inventory i
JOIN drugs d ON i.drug_id = d.drug_id;

-- =============================================================================
-- 2. PRESCRIPTION FILL RATE ANALYSIS
-- =============================================================================
SELECT
    d.therapy_area,
    d.is_specialty,
    COUNT(r.rx_id)                                      AS total_rx,
    COUNT(*) FILTER (WHERE r.is_filled = TRUE)          AS filled_rx,
    COUNT(*) FILTER (WHERE r.is_filled = FALSE)         AS unfilled_rx,
    ROUND(COUNT(*) FILTER (WHERE r.is_filled = TRUE)
        * 100.0 / COUNT(*), 2)                          AS fill_rate_pct,
    ROUND(AVG(r.days_to_fill)
          FILTER (WHERE r.is_filled = TRUE), 1)         AS avg_days_to_fill,
    ROUND(SUM(r.total_cost_usd), 2)                     AS total_dispensed_value
FROM prescriptions r
JOIN drugs d ON r.drug_id = d.drug_id
GROUP BY d.therapy_area, d.is_specialty
ORDER BY fill_rate_pct, d.therapy_area;

-- =============================================================================
-- 3. DAYS ON HAND (DOH) BY DRUG — Inventory Efficiency
-- =============================================================================
SELECT
    d.brand_name,
    d.generic_name,
    d.therapy_area,
    d.is_specialty,
    d.avg_monthly_units,
    SUM(i.available_units)                              AS total_available,
    ROUND(AVG(i.days_on_hand), 1)                       AS avg_doh,
    MIN(i.days_on_hand)                                 AS min_doh_warehouse,
    MAX(i.days_on_hand)                                 AS max_doh_warehouse,
    ROUND(SUM(i.available_units * i.unit_cost_usd), 2)  AS inventory_value_usd,
    CASE
        WHEN MIN(i.days_on_hand) = 0    THEN 'STOCKOUT'
        WHEN MIN(i.days_on_hand) < 15   THEN 'CRITICAL'
        WHEN MIN(i.days_on_hand) < 30   THEN 'LOW'
        WHEN MIN(i.days_on_hand) > 90   THEN 'OVERSTOCK'
        ELSE 'HEALTHY'
    END                                                 AS doh_status
FROM inventory i
JOIN drugs d ON i.drug_id = d.drug_id
GROUP BY d.drug_id, d.brand_name, d.generic_name,
         d.therapy_area, d.is_specialty, d.avg_monthly_units
ORDER BY avg_doh;

-- =============================================================================
-- 4. SUPPLIER PERFORMANCE SCORECARD
-- =============================================================================
SELECT
    s.supplier_name,
    s.supplier_type,
    s.performance_grade,
    s.lead_time_days                                    AS contracted_lead_days,
    COUNT(po.po_id)                                     AS total_orders,
    ROUND(SUM(po.total_cost_usd), 2)                    AS total_spend_usd,
    COUNT(*) FILTER (WHERE po.on_time_delivery = TRUE)  AS on_time_orders,
    COUNT(*) FILTER (WHERE po.on_time_delivery = FALSE) AS late_orders,
    ROUND(COUNT(*) FILTER (WHERE po.on_time_delivery = TRUE)
        * 100.0 / NULLIF(COUNT(*),0), 2)                AS actual_on_time_pct,
    ROUND(AVG(po.delay_days)
          FILTER (WHERE po.on_time_delivery = FALSE), 1) AS avg_delay_days,
    ROUND(SUM(po.total_cost_usd)
        * 100.0 / SUM(SUM(po.total_cost_usd)) OVER (), 2) AS pct_of_total_spend
FROM suppliers s
LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.supplier_type,
         s.performance_grade, s.lead_time_days
ORDER BY total_spend_usd DESC;

-- =============================================================================
-- 5. STOCKOUT ANALYSIS — Root Cause & Revenue Impact
-- =============================================================================
SELECT
    st.root_cause,
    COUNT(*)                                            AS stockout_events,
    ROUND(AVG(st.duration_days), 1)                     AS avg_duration_days,
    SUM(st.lost_rx_count)                               AS total_lost_rx,
    ROUND(SUM(st.lost_revenue_usd), 2)                  AS total_lost_revenue,
    ROUND(AVG(st.lost_revenue_usd), 2)                  AS avg_lost_revenue_per_event,
    COUNT(DISTINCT st.drug_id)                          AS drugs_affected,
    COUNT(DISTINCT st.warehouse_id)                     AS warehouses_affected
FROM stockout_events st
GROUP BY st.root_cause
ORDER BY total_lost_revenue DESC;

-- =============================================================================
-- 6. PURCHASE ORDER CYCLE TIME ANALYSIS
-- =============================================================================
SELECT
    s.supplier_name,
    s.performance_grade,
    d.therapy_area,
    COUNT(po.po_id)                                     AS total_pos,
    ROUND(AVG(po.total_units), 0)                       AS avg_order_qty,
    ROUND(AVG(po.total_cost_usd), 2)                    AS avg_order_value,
    ROUND(AVG(EXTRACT(DAY FROM (po.actual_receipt_date::TIMESTAMP
        - po.order_date::TIMESTAMP))), 1)                AS actual_cycle_days,
    s.lead_time_days                                    AS contracted_cycle_days,
    ROUND(AVG(po.delay_days), 1)                        AS avg_delay_days,
    ROUND(COUNT(*) FILTER (WHERE po.on_time_delivery)
        * 100.0 / COUNT(*), 2)                          AS on_time_pct
FROM purchase_orders po
JOIN suppliers s ON po.supplier_id = s.supplier_id
JOIN drugs d     ON po.drug_id     = d.drug_id
WHERE po.status = 'Received'
GROUP BY s.supplier_id, s.supplier_name, s.performance_grade,
         d.therapy_area, s.lead_time_days
ORDER BY avg_delay_days DESC;

-- =============================================================================
-- 7. SPECIALTY VS NON-SPECIALTY DRUG ANALYSIS
-- =============================================================================
SELECT
    d.is_specialty,
    d.therapy_area,
    COUNT(DISTINCT d.drug_id)                           AS drug_count,
    COUNT(r.rx_id)                                      AS total_rx,
    ROUND(SUM(r.total_cost_usd), 2)                     AS total_spend,
    ROUND(AVG(r.total_cost_usd)
          FILTER (WHERE r.is_filled), 2)                AS avg_rx_cost,
    ROUND(COUNT(*) FILTER (WHERE r.is_filled)
        * 100.0 / COUNT(*), 2)                          AS fill_rate_pct,
    ROUND(SUM(i.available_units * i.unit_cost_usd), 2)  AS inventory_value
FROM drugs d
LEFT JOIN prescriptions r ON d.drug_id = r.drug_id
LEFT JOIN inventory i     ON d.drug_id = i.drug_id
GROUP BY d.is_specialty, d.therapy_area
ORDER BY d.is_specialty DESC, total_spend DESC;

-- =============================================================================
-- 8. WAREHOUSE INVENTORY DISTRIBUTION
-- =============================================================================
SELECT
    w.warehouse_name,
    w.region,
    w.has_cold_storage,
    COUNT(DISTINCT i.drug_id)                           AS total_skus,
    SUM(i.available_units)                              AS total_available_units,
    ROUND(SUM(i.available_units * i.unit_cost_usd), 2)  AS total_inventory_value,
    ROUND(AVG(i.days_on_hand), 1)                       AS avg_days_on_hand,
    COUNT(*) FILTER (WHERE i.is_below_reorder)          AS skus_below_reorder,
    COUNT(*) FILTER (WHERE i.is_stockout_risk)          AS skus_at_risk,
    ROUND(SUM(i.available_units) * 100.0
        / w.capacity_units, 2)                          AS capacity_utilization_pct
FROM warehouses w
JOIN inventory i ON w.warehouse_id = i.warehouse_id
GROUP BY w.warehouse_id, w.warehouse_name, w.region,
         w.has_cold_storage, w.capacity_units
ORDER BY total_inventory_value DESC;

-- =============================================================================
-- 9. MONTHLY PRESCRIPTION TREND WITH WINDOW FUNCTIONS
-- =============================================================================
SELECT
    TO_CHAR(DATE_TRUNC('month', rx_date), 'YYYY-MM')   AS month,
    COUNT(*)                                            AS total_rx,
    COUNT(*) FILTER (WHERE is_filled)                   AS filled_rx,
    ROUND(COUNT(*) FILTER (WHERE is_filled)
        * 100.0 / COUNT(*), 2)                          AS fill_rate_pct,
    ROUND(SUM(total_cost_usd), 2)                       AS total_spend,
    ROUND(AVG(days_to_fill)
          FILTER (WHERE is_filled), 1)                  AS avg_days_to_fill,
    ROUND(SUM(SUM(total_cost_usd)) OVER (
        ORDER BY DATE_TRUNC('month', rx_date)), 2)       AS cumulative_spend,
    ROUND(COUNT(*) - LAG(COUNT(*)) OVER (
        ORDER BY DATE_TRUNC('month', rx_date)), 0)       AS rx_mom_change
FROM prescriptions
GROUP BY DATE_TRUNC('month', rx_date)
ORDER BY month;

-- =============================================================================
-- 10. REORDER ALERT — Drugs Needing Immediate Procurement
-- =============================================================================
SELECT
    d.brand_name,
    d.generic_name,
    d.therapy_area,
    d.is_specialty,
    s.supplier_name,
    s.lead_time_days,
    s.performance_grade,
    i.warehouse_id,
    i.available_units,
    i.reorder_point,
    i.safety_stock,
    i.days_on_hand,
    (d.avg_monthly_units * 2)                           AS recommended_order_qty,
    ROUND((d.avg_monthly_units * 2 * d.unit_cost_usd), 2) AS estimated_po_cost,
    CASE
        WHEN i.available_units = 0  THEN '🚨 STOCKOUT'
        WHEN i.is_stockout_risk     THEN '🔴 CRITICAL'
        ELSE '🟡 REORDER NOW'
    END                                                 AS priority
FROM inventory i
JOIN drugs d     ON i.drug_id             = d.drug_id
JOIN suppliers s ON d.primary_supplier_id = s.supplier_id
WHERE i.is_below_reorder = TRUE
ORDER BY i.days_on_hand, d.is_specialty DESC;

-- =============================================================================
-- 11. DATA QUALITY CHECKS
-- =============================================================================
SELECT 'inventory_negative_units'     AS check_name,
       COUNT(*)                       AS issues
FROM inventory WHERE available_units < 0
UNION ALL
SELECT 'po_receipt_before_order',     COUNT(*)
FROM purchase_orders
WHERE actual_receipt_date < order_date
UNION ALL
SELECT 'rx_fill_before_rx_date',      COUNT(*)
FROM prescriptions
WHERE fill_date < rx_date
UNION ALL
SELECT 'stockout_end_before_start',   COUNT(*)
FROM stockout_events
WHERE end_date < start_date
UNION ALL
SELECT 'drugs_missing_ndc',           COUNT(*)
FROM drugs WHERE ndc IS NULL
UNION ALL
SELECT 'inventory_exceeds_capacity',  COUNT(*)
FROM inventory i
JOIN warehouses w ON i.warehouse_id = w.warehouse_id
WHERE i.current_units > w.capacity_units;
