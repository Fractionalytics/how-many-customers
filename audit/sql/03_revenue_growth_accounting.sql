-- 03_revenue_growth_accounting.sql : revenue growth accounting, quick ratio, NRR and GRR.
-- Follows the TheVentureCity toolkit definitions (calc_rev_ga): per customer per month,
--   new         = revenue in the customer's first month
--   retained    = min(this month, last month) where both > 0
--   expansion   = this - last where both > 0 and this > last
--   contraction = this - last where both > 0 and this < last   (negative)
--   resurrected = this month > 0, last month = 0, not the first month
--   churned     = -last month where this month = 0 and last month > 0 (negative)
--   quick ratio = (new + resurrected + expansion) / -(churned + contraction)
-- Run twice: on RECOGNIZED revenue (annual invoices spread over 12 months) and on CASH.
-- The same invoices tell two different stories, and only one of them is about the customers.

CREATE OR REPLACE MACRO ga_table(tbl) AS TABLE
  SELECT month,
         COUNT(*) FILTER (WHERE rev > 0)                                                   AS paying_customers,
         SUM(rev)                                                                          AS revenue,
         SUM(CASE WHEN months_since_first = 0 THEN rev END)                                AS new_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev_prev > 0
                  THEN LEAST(rev, rev_prev) END)                                           AS retained_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > rev_prev AND rev_prev > 0
                  THEN rev - rev_prev END)                                                 AS expansion_rev,
        -SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev < rev_prev
                  THEN rev_prev - rev END)                                                 AS contraction_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev_prev = 0 THEN rev END)   AS resurrected_rev,
        -SUM(CASE WHEN rev = 0 AND rev_prev > 0 THEN rev_prev END)                         AS churned_rev
  FROM query_table(tbl) GROUP BY 1;

CREATE OR REPLACE VIEW rev_ga_recognized AS
  SELECT *, ROUND((COALESCE(new_rev,0) + COALESCE(resurrected_rev,0) + COALESCE(expansion_rev,0))
              / NULLIF(-(COALESCE(churned_rev,0) + COALESCE(contraction_rev,0)), 0), 2) AS quick_ratio
  FROM ga_table('panel');

CREATE OR REPLACE VIEW rev_ga_cash AS
  SELECT *, ROUND((COALESCE(new_rev,0) + COALESCE(resurrected_rev,0) + COALESCE(expansion_rev,0))
              / NULLIF(-(COALESCE(churned_rev,0) + COALESCE(contraction_rev,0)), 0), 2) AS quick_ratio
  FROM ga_table('panel_cash');

-- Monthly series, recognized basis. The as-of month (2026-08) is PARTIAL: 20 days of monthly
-- invoices. Read its churn as an artifact, not a signal.
-- @out rev_ga_recognized_monthly
SELECT month, paying_customers, ROUND(revenue) AS revenue, ROUND(new_rev) AS new_rev, ROUND(retained_rev) AS retained_rev,
       ROUND(expansion_rev) AS expansion_rev, ROUND(contraction_rev) AS contraction_rev,
       ROUND(resurrected_rev) AS resurrected_rev, ROUND(churned_rev) AS churned_rev, quick_ratio
FROM rev_ga_recognized ORDER BY month;

-- @out rev_ga_cash_monthly
SELECT month, paying_customers, ROUND(revenue) AS revenue, ROUND(new_rev) AS new_rev, ROUND(retained_rev) AS retained_rev,
       ROUND(expansion_rev) AS expansion_rev, ROUND(contraction_rev) AS contraction_rev,
       ROUND(resurrected_rev) AS resurrected_rev, ROUND(churned_rev) AS churned_rev, quick_ratio
FROM rev_ga_cash ORDER BY month;

-- The two bases side by side over the last 12 complete months. Same invoices.
-- @out recognized_vs_cash_last_12
WITH r AS (SELECT * FROM rev_ga_recognized), c AS (SELECT * FROM rev_ga_cash), p AS (SELECT as_of FROM params)
SELECT 'recognized' AS basis,
       ROUND(AVG(quick_ratio), 2) AS mean_quick_ratio, ROUND(MIN(quick_ratio), 2) AS min_qr, ROUND(MAX(quick_ratio), 2) AS max_qr,
       ROUND(SUM(-churned_rev) / SUM(revenue) * 100, 1) AS churned_pct_of_revenue,
       ROUND(SUM(resurrected_rev) / SUM(revenue) * 100, 1) AS resurrected_pct_of_revenue
FROM r, p WHERE month < date_trunc('month', as_of) AND month >= date_trunc('month', as_of) - INTERVAL 12 MONTH
UNION ALL
SELECT 'cash', ROUND(AVG(quick_ratio), 2), ROUND(MIN(quick_ratio), 2), ROUND(MAX(quick_ratio), 2),
       ROUND(SUM(-churned_rev) / SUM(revenue) * 100, 1), ROUND(SUM(resurrected_rev) / SUM(revenue) * 100, 1)
FROM c, p WHERE month < date_trunc('month', as_of) AND month >= date_trunc('month', as_of) - INTERVAL 12 MONTH;

-- Net and gross revenue retention, trailing twelve months, recognized basis.
-- NRR(m) = revenue in m from customers who paid in m-12, over their revenue in m-12.
-- GRR(m) = same, capped at each customer's m-12 revenue (no expansion credit).
CREATE OR REPLACE VIEW nrr AS
  SELECT a.month,
         COUNT(*) AS base_customers,
         COUNT(*) FILTER (WHERE b.rev > 0) AS still_paying,
         ROUND(SUM(b.rev) / SUM(a.rev) * 100, 1) AS nrr_pct,
         ROUND(SUM(LEAST(b.rev, a.rev)) / SUM(a.rev) * 100, 1) AS grr_pct,
         ROUND(100.0 * COUNT(*) FILTER (WHERE b.rev > 0) / COUNT(*), 1) AS logo_retention_pct
  FROM panel a
  JOIN panel b ON b.customer_ref = a.customer_ref AND b.month = (a.month + INTERVAL 12 MONTH)::DATE
  WHERE a.rev > 0
  GROUP BY 1;

-- The month column is the BASE month; the retention is measured twelve months later.
-- @out nrr_monthly
SELECT month AS base_month, (month + INTERVAL 12 MONTH)::DATE AS measured_month,
       base_customers, still_paying, logo_retention_pct, grr_pct, nrr_pct
FROM nrr, params WHERE (month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of) ORDER BY month;

-- @out nrr_summary_last_12_base_months
SELECT ROUND(AVG(nrr_pct), 1) AS mean_nrr_pct, ROUND(AVG(grr_pct), 1) AS mean_grr_pct,
       ROUND(AVG(logo_retention_pct), 1) AS mean_logo_retention_pct,
       MIN(month) AS from_base_month, MAX(month) AS to_base_month
FROM nrr, params
WHERE (month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
  AND month >= date_trunc('month', as_of) - INTERVAL 24 MONTH;

-- Same NRR on the cash basis, to show how far the annual invoices swing it.
-- @out nrr_cash_vs_recognized
WITH cash AS (
  SELECT a.month, ROUND(SUM(b.rev) / SUM(a.rev) * 100, 1) AS nrr_cash_pct
  FROM panel_cash a JOIN panel_cash b ON b.customer_ref = a.customer_ref AND b.month = (a.month + INTERVAL 12 MONTH)::DATE
  WHERE a.rev > 0 GROUP BY 1)
SELECT n.month AS base_month, n.nrr_pct AS nrr_recognized_pct, c.nrr_cash_pct
FROM nrr n JOIN cash c USING (month), params
WHERE (n.month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
  AND n.month >= date_trunc('month', as_of) - INTERVAL 24 MONTH
ORDER BY 1;

-- ------------------------------------------------------------ by contract type
-- Monthly, annual and usage customers are three different businesses in one ledger. Blending
-- them compares apples to oranges, so every growth-accounting figure is repeated per contract.
CREATE OR REPLACE VIEW rev_ga_by_contract AS
  SELECT contract_type, month,
         COUNT(*) FILTER (WHERE rev > 0)                                                   AS paying_customers,
         SUM(rev)                                                                          AS revenue,
         SUM(CASE WHEN months_since_first = 0 THEN rev END)                                AS new_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev_prev > 0
                  THEN LEAST(rev, rev_prev) END)                                           AS retained_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > rev_prev AND rev_prev > 0
                  THEN rev - rev_prev END)                                                 AS expansion_rev,
        -SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev < rev_prev
                  THEN rev_prev - rev END)                                                 AS contraction_rev,
         SUM(CASE WHEN months_since_first > 0 AND rev > 0 AND rev_prev = 0 THEN rev END)   AS resurrected_rev,
        -SUM(CASE WHEN rev = 0 AND rev_prev > 0 THEN rev_prev END)                         AS churned_rev
  FROM panel_c GROUP BY 1, 2;

-- @out rev_ga_by_contract_monthly
SELECT contract_type, month, paying_customers, ROUND(revenue) AS revenue, ROUND(new_rev) AS new_rev,
       ROUND(retained_rev) AS retained_rev, ROUND(expansion_rev) AS expansion_rev, ROUND(contraction_rev) AS contraction_rev,
       ROUND(resurrected_rev) AS resurrected_rev, ROUND(churned_rev) AS churned_rev,
       ROUND((COALESCE(new_rev,0) + COALESCE(resurrected_rev,0) + COALESCE(expansion_rev,0))
             / NULLIF(-(COALESCE(churned_rev,0) + COALESCE(contraction_rev,0)), 0), 2) AS quick_ratio
FROM rev_ga_by_contract ORDER BY contract_type, month;

-- @out rev_ga_by_contract_last_12
SELECT contract_type,
       ROUND(SUM(revenue)) AS revenue_12m,
       ROUND(100.0 * SUM(new_rev) / SUM(revenue), 1) AS new_pct,
       ROUND(100.0 * SUM(expansion_rev) / SUM(revenue), 1) AS expansion_pct,
       ROUND(100.0 * SUM(contraction_rev) / SUM(revenue), 1) AS contraction_pct,
       ROUND(100.0 * SUM(resurrected_rev) / SUM(revenue), 1) AS resurrected_pct,
       ROUND(100.0 * SUM(churned_rev) / SUM(revenue), 1) AS churned_pct,
       ROUND((SUM(new_rev) + SUM(resurrected_rev) + SUM(expansion_rev)) / NULLIF(-(SUM(churned_rev) + SUM(contraction_rev)), 0), 2) AS quick_ratio_12m
FROM rev_ga_by_contract, params
WHERE month < date_trunc('month', as_of) AND month >= date_trunc('month', as_of) - INTERVAL 12 MONTH
GROUP BY 1 ORDER BY 2 DESC;

-- NRR by contract type, base month to twelve months later.
CREATE OR REPLACE VIEW nrr_by_contract AS
  SELECT a.contract_type, a.month,
         COUNT(*) AS base_customers,
         ROUND(SUM(b.rev) / SUM(a.rev) * 100, 1) AS nrr_pct,
         ROUND(SUM(LEAST(b.rev, a.rev)) / SUM(a.rev) * 100, 1) AS grr_pct,
         ROUND(100.0 * COUNT(*) FILTER (WHERE b.rev > 0) / COUNT(*), 1) AS logo_retention_pct
  FROM panel_c a
  JOIN panel b ON b.customer_ref = a.customer_ref AND b.month = (a.month + INTERVAL 12 MONTH)::DATE
  WHERE a.rev > 0
  GROUP BY 1, 2;

-- @out nrr_by_contract_monthly
SELECT contract_type, month AS base_month, base_customers, logo_retention_pct, grr_pct, nrr_pct
FROM nrr_by_contract, params WHERE (month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
ORDER BY contract_type, month;

-- @out nrr_by_contract_last_12_base_months
SELECT contract_type, ROUND(AVG(nrr_pct), 1) AS mean_nrr_pct, ROUND(AVG(grr_pct), 1) AS mean_grr_pct,
       ROUND(AVG(logo_retention_pct), 1) AS mean_logo_retention_pct
FROM nrr_by_contract, params
WHERE (month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
  AND month >= date_trunc('month', as_of) - INTERVAL 24 MONTH
GROUP BY 1 ORDER BY 1;
