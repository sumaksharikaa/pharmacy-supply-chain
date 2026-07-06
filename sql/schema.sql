-- =============================================================================
-- schema.sql
-- Pharmacy Supply Chain & Prescription Analytics — PostgreSQL Schema
-- Written in Oracle-compatible SQL style (uses standard ANSI SQL supported
-- by both PostgreSQL and Oracle — no PostgreSQL-specific syntax)
-- =============================================================================

-- ── drop existing ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS stockout_events     CASCADE;
DROP TABLE IF EXISTS prescriptions       CASCADE;
DROP TABLE IF EXISTS inventory           CASCADE;
DROP TABLE IF EXISTS purchase_orders     CASCADE;
DROP TABLE IF EXISTS drugs               CASCADE;
DROP TABLE IF EXISTS warehouses          CASCADE;
DROP TABLE IF EXISTS suppliers           CASCADE;
DROP TABLE IF EXISTS audit_log           CASCADE;

-- =============================================================================
-- DIMENSION TABLES
-- =============================================================================

CREATE TABLE suppliers (
    supplier_id         VARCHAR(10)     NOT NULL,
    supplier_name       VARCHAR(100)    NOT NULL,
    supplier_type       VARCHAR(40)     NOT NULL,
    state               CHAR(2)         NOT NULL,
    performance_grade   CHAR(1)         NOT NULL CHECK (performance_grade IN ('A','B','C','D','F')),
    lead_time_days      SMALLINT        NOT NULL CHECK (lead_time_days > 0),
    on_time_rate        NUMERIC(5,3)    NOT NULL CHECK (on_time_rate BETWEEN 0 AND 1),
    fill_rate           NUMERIC(5,3)    NOT NULL CHECK (fill_rate BETWEEN 0 AND 1),
    contract_start      DATE            NOT NULL,
    is_preferred        BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_suppliers PRIMARY KEY (supplier_id)
);

CREATE TABLE warehouses (
    warehouse_id        VARCHAR(10)     NOT NULL,
    warehouse_name      VARCHAR(100)    NOT NULL,
    city                VARCHAR(50)     NOT NULL,
    state               CHAR(2)         NOT NULL,
    region              VARCHAR(30),
    has_cold_storage    BOOLEAN         NOT NULL DEFAULT FALSE,
    capacity_units      INTEGER         NOT NULL CHECK (capacity_units > 0),
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_warehouses PRIMARY KEY (warehouse_id)
);

CREATE TABLE drugs (
    drug_id                 VARCHAR(10)     NOT NULL,
    brand_name              VARCHAR(100)    NOT NULL,
    generic_name            VARCHAR(100)    NOT NULL,
    primary_supplier_id     VARCHAR(10)     NOT NULL,
    therapy_area            VARCHAR(60)     NOT NULL,
    dosage_form             VARCHAR(30)     NOT NULL,
    strength                VARCHAR(20)     NOT NULL,
    ndc                     VARCHAR(20),
    unit_cost_usd           NUMERIC(10,2)   NOT NULL CHECK (unit_cost_usd > 0),
    is_specialty            BOOLEAN         NOT NULL DEFAULT FALSE,
    requires_cold_chain     BOOLEAN         NOT NULL DEFAULT FALSE,
    days_supply_std         SMALLINT        NOT NULL,
    avg_monthly_units       INTEGER         NOT NULL CHECK (avg_monthly_units > 0),
    reorder_point_units     INTEGER         NOT NULL,
    safety_stock_units      INTEGER         NOT NULL,
    created_at              TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_drugs PRIMARY KEY (drug_id),
    CONSTRAINT fk_drugs_supplier FOREIGN KEY (primary_supplier_id)
        REFERENCES suppliers(supplier_id)
);

-- =============================================================================
-- FACT TABLES
-- =============================================================================

CREATE TABLE inventory (
    inventory_id        VARCHAR(12)     NOT NULL,
    drug_id             VARCHAR(10)     NOT NULL,
    warehouse_id        VARCHAR(10)     NOT NULL,
    current_units       INTEGER         NOT NULL DEFAULT 0,
    reserved_units      INTEGER         NOT NULL DEFAULT 0,
    available_units     INTEGER         NOT NULL DEFAULT 0,
    unit_cost_usd       NUMERIC(10,2)   NOT NULL,
    reorder_point       INTEGER         NOT NULL,
    safety_stock        INTEGER         NOT NULL,
    days_on_hand        NUMERIC(6,1),
    is_below_reorder    BOOLEAN         DEFAULT FALSE,
    is_stockout_risk    BOOLEAN         DEFAULT FALSE,
    expiry_date         DATE,
    last_updated        DATE            NOT NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_inventory PRIMARY KEY (inventory_id),
    CONSTRAINT fk_inv_drug  FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),
    CONSTRAINT fk_inv_wh    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    CONSTRAINT uq_inv_drug_wh UNIQUE (drug_id, warehouse_id)
);

CREATE INDEX idx_inv_drug      ON inventory(drug_id);
CREATE INDEX idx_inv_wh        ON inventory(warehouse_id);
CREATE INDEX idx_inv_reorder   ON inventory(is_below_reorder);
CREATE INDEX idx_inv_stockout  ON inventory(is_stockout_risk);

CREATE TABLE purchase_orders (
    po_id               VARCHAR(10)     NOT NULL,
    supplier_id         VARCHAR(10)     NOT NULL,
    warehouse_id        VARCHAR(10)     NOT NULL,
    drug_id             VARCHAR(10)     NOT NULL,
    order_date          DATE            NOT NULL,
    expected_date       DATE            NOT NULL,
    actual_receipt_date DATE,
    status              VARCHAR(20)     NOT NULL CHECK (status IN ('Pending','Received','Cancelled','Partial')),
    on_time_delivery    BOOLEAN,
    delay_days          SMALLINT        DEFAULT 0,
    total_units         INTEGER         NOT NULL CHECK (total_units > 0),
    unit_cost_usd       NUMERIC(10,2)   NOT NULL,
    total_cost_usd      NUMERIC(12,2)   NOT NULL,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_po PRIMARY KEY (po_id),
    CONSTRAINT fk_po_supplier  FOREIGN KEY (supplier_id)  REFERENCES suppliers(supplier_id),
    CONSTRAINT fk_po_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT fk_po_drug      FOREIGN KEY (drug_id)      REFERENCES drugs(drug_id),
    CONSTRAINT chk_receipt_after_order CHECK (
        actual_receipt_date IS NULL OR actual_receipt_date >= order_date
    )
);

CREATE INDEX idx_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX idx_po_drug     ON purchase_orders(drug_id);
CREATE INDEX idx_po_status   ON purchase_orders(status);
CREATE INDEX idx_po_date     ON purchase_orders(order_date);

CREATE TABLE prescriptions (
    rx_id               VARCHAR(12)     NOT NULL,
    patient_id          VARCHAR(10)     NOT NULL,
    drug_id             VARCHAR(10)     NOT NULL,
    warehouse_id        VARCHAR(10)     NOT NULL,
    rx_date             DATE            NOT NULL,
    fill_date           DATE,
    days_to_fill        SMALLINT,
    quantity_dispensed  SMALLINT        NOT NULL DEFAULT 0,
    days_supply         SMALLINT        NOT NULL,
    is_filled           BOOLEAN         NOT NULL DEFAULT FALSE,
    fill_status         VARCHAR(50),
    unit_cost_usd       NUMERIC(10,2),
    total_cost_usd      NUMERIC(10,2)   DEFAULT 0,
    is_specialty        BOOLEAN         DEFAULT FALSE,
    therapy_area        VARCHAR(60),
    refill_number       SMALLINT        DEFAULT 0,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_prescriptions PRIMARY KEY (rx_id),
    CONSTRAINT fk_rx_drug FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),
    CONSTRAINT fk_rx_wh  FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    CONSTRAINT chk_fill_after_rx CHECK (
        fill_date IS NULL OR fill_date >= rx_date
    )
);

CREATE INDEX idx_rx_drug      ON prescriptions(drug_id);
CREATE INDEX idx_rx_patient   ON prescriptions(patient_id);
CREATE INDEX idx_rx_date      ON prescriptions(rx_date);
CREATE INDEX idx_rx_filled    ON prescriptions(is_filled);
CREATE INDEX idx_rx_specialty ON prescriptions(is_specialty);

CREATE TABLE stockout_events (
    stockout_id         VARCHAR(10)     NOT NULL,
    drug_id             VARCHAR(10)     NOT NULL,
    warehouse_id        VARCHAR(10)     NOT NULL,
    start_date          DATE            NOT NULL,
    end_date            DATE            NOT NULL,
    duration_days       SMALLINT        NOT NULL CHECK (duration_days >= 0),
    lost_rx_count       INTEGER         DEFAULT 0,
    lost_revenue_usd    NUMERIC(12,2)   DEFAULT 0,
    root_cause          VARCHAR(50),
    resolved            BOOLEAN         DEFAULT FALSE,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_stockout PRIMARY KEY (stockout_id),
    CONSTRAINT fk_stk_drug FOREIGN KEY (drug_id)
        REFERENCES drugs(drug_id),
    CONSTRAINT fk_stk_wh   FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id),
    CONSTRAINT chk_end_after_start CHECK (end_date >= start_date)
);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================
CREATE TABLE audit_log (
    log_id          SERIAL          PRIMARY KEY,
    table_name      VARCHAR(50)     NOT NULL,
    record_id       VARCHAR(20)     NOT NULL,
    action          VARCHAR(10)     NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
    changed_by      VARCHAR(50)     DEFAULT current_user,
    changed_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    old_values      JSONB,
    new_values      JSONB
);

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Current inventory status with reorder alerts
CREATE OR REPLACE VIEW vw_inventory_alerts AS
SELECT
    i.drug_id,
    d.brand_name,
    d.therapy_area,
    d.is_specialty,
    i.warehouse_id,
    w.warehouse_name,
    w.region,
    i.current_units,
    i.available_units,
    i.reorder_point,
    i.safety_stock,
    i.days_on_hand,
    i.is_below_reorder,
    i.is_stockout_risk,
    CASE
        WHEN i.available_units = 0           THEN 'STOCKOUT'
        WHEN i.is_stockout_risk              THEN 'CRITICAL'
        WHEN i.is_below_reorder              THEN 'REORDER NOW'
        WHEN i.days_on_hand < 30             THEN 'LOW STOCK'
        ELSE 'OK'
    END AS alert_level
FROM inventory i
JOIN drugs d      ON i.drug_id      = d.drug_id
JOIN warehouses w ON i.warehouse_id = w.warehouse_id
ORDER BY
    CASE WHEN i.available_units = 0     THEN 1
         WHEN i.is_stockout_risk        THEN 2
         WHEN i.is_below_reorder        THEN 3
         ELSE 4 END,
    i.days_on_hand;

-- Supplier scorecard
CREATE OR REPLACE VIEW vw_supplier_scorecard AS
SELECT
    s.supplier_id,
    s.supplier_name,
    s.supplier_type,
    s.performance_grade,
    s.lead_time_days,
    s.on_time_rate,
    s.fill_rate,
    COUNT(po.po_id)                                     AS total_orders,
    ROUND(SUM(po.total_cost_usd)::NUMERIC, 2)           AS total_spend_usd,
    ROUND(AVG(po.delay_days)::NUMERIC, 1)               AS avg_delay_days,
    COUNT(*) FILTER (WHERE po.on_time_delivery = TRUE)  AS on_time_orders,
    COUNT(*) FILTER (WHERE po.on_time_delivery = FALSE) AS late_orders
FROM suppliers s
LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.supplier_type,
         s.performance_grade, s.lead_time_days, s.on_time_rate, s.fill_rate
ORDER BY total_spend_usd DESC;

-- =============================================================================
-- STORED PROCEDURE: Reorder Recommendation
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_reorder_recommendation(p_warehouse_id VARCHAR)
RETURNS TABLE (
    drug_id         VARCHAR,
    brand_name      VARCHAR,
    supplier_name   VARCHAR,
    available_units INT,
    days_on_hand    NUMERIC,
    recommended_qty INT,
    estimated_cost  NUMERIC,
    alert_level     TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.drug_id::VARCHAR,
        d.brand_name::VARCHAR,
        s.supplier_name::VARCHAR,
        i.available_units::INT,
        i.days_on_hand,
        (d.avg_monthly_units * 2)::INT                      AS recommended_qty,
        ROUND((d.avg_monthly_units * 2 * d.unit_cost_usd)::NUMERIC, 2) AS estimated_cost,
        CASE
            WHEN i.available_units = 0   THEN 'STOCKOUT'
            WHEN i.is_stockout_risk      THEN 'CRITICAL'
            ELSE 'REORDER NOW'
        END::TEXT AS alert_level
    FROM inventory i
    JOIN drugs d      ON i.drug_id         = d.drug_id
    JOIN suppliers s  ON d.primary_supplier_id = s.supplier_id
    WHERE i.warehouse_id = p_warehouse_id
      AND i.is_below_reorder = TRUE
    ORDER BY i.days_on_hand;
END;
$$ LANGUAGE plpgsql;
