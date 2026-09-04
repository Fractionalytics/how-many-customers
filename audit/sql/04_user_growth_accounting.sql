-- 04_user_growth_accounting.sql : active-organization growth accounting from the telemetry.
-- Toolkit definitions (calc_user_ga), with the organization as the unit:
--   active      = any usage in the month
--   new         = first month with usage
--   retained    = active this month and last
--   resurrected = active this month, not last, not first
--   churned     = active last month, not this   (negative)
--   quick ratio = (new + resurrected) / -churned
-- This is a customer count that comes from a THIRD system and a fourth definition, and it
-- has its own censoring: the log starts 2025-07-17, so every org is "new" in its first
-- observed month whether or not it was a customer for years.

CREATE OR REPLACE VIEW user_ga AS
  SELECT month,
         COUNT(*) FILTER (WHERE act > 0)                                        AS active_orgs,
         COUNT(*) FILTER (WHERE months_since_first = 0 AND act > 0)             AS new_orgs,
         COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev > 0) AS retained_orgs,
         COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev = 0) AS resurrected_orgs,
        -COUNT(*) FILTER (WHERE act = 0 AND act_prev > 0)                       AS churned_orgs
  FROM (SELECT *, date_diff('month', first_month, month) AS months_since_first FROM usage_panel)
  GROUP BY 1;

-- @out user_ga_monthly
SELECT month, active_orgs, new_orgs, retained_orgs, resurrected_orgs, churned_orgs,
       ROUND((new_orgs + resurrected_orgs) / NULLIF(-churned_orgs, 0)::DOUBLE, 2) AS quick_ratio,
       ROUND(100.0 * retained_orgs / NULLIF(LAG(active_orgs) OVER (ORDER BY month), 0), 1) AS mom_retention_pct
FROM user_ga ORDER BY month;

-- Telemetry depth: how much history the product log actually holds against billing.
-- @out telemetry_depth
SELECT 'product_usage' AS source, MIN(event_date) AS first_date, MAX(event_date) AS last_date,
       date_diff('month', MIN(event_date), MAX(event_date)) + 1 AS months_of_history FROM usage
UNION ALL
SELECT 'billing_invoices', MIN(invoice_date), MAX(invoice_date), date_diff('month', MIN(invoice_date), MAX(invoice_date)) + 1 FROM inv
UNION ALL
SELECT 'crm_accounts (created_date)', MIN(created_date), MAX(created_date), date_diff('month', MIN(created_date), MAX(created_date)) + 1 FROM crm
UNION ALL
SELECT 'marketing_spend', MIN(month || '-01')::DATE, MAX(month || '-01')::DATE, COUNT(DISTINCT month) FROM spend;

-- Paying-versus-using, month by month, through the entity resolver. Billing knows who pays;
-- telemetry knows who shows up. Paying customers reach the telemetry key through the bridge,
-- so an unmatched billing customer counts as "paying, not using" whether or not it uses.
CREATE OR REPLACE VIEW pay_use AS
  WITH paying AS (
    SELECT DISTINCT e.entity_k AS k, r.month FROM rev_amort r JOIN bill_entity e USING (customer_ref) WHERE r.rev > 0),
  using_ AS (
    SELECT DISTINCT entity_k AS k, month FROM usage_month)
  SELECT COALESCE(p.month, u.month) AS month,
         COUNT(*) FILTER (WHERE p.k IS NOT NULL AND u.k IS NOT NULL) AS paying_and_using,
         COUNT(*) FILTER (WHERE p.k IS NOT NULL AND u.k IS NULL)     AS paying_not_using,
         COUNT(*) FILTER (WHERE p.k IS NULL AND u.k IS NOT NULL)     AS using_not_paying
  FROM paying p FULL OUTER JOIN using_ u ON u.k = p.k AND u.month = p.month
  WHERE COALESCE(p.month, u.month) >= (SELECT MIN(month) FROM usage_month)
  GROUP BY 1;

-- @out paying_vs_using_monthly
SELECT * FROM pay_use ORDER BY month;

-- @out paying_vs_using_last_complete_month
SELECT * FROM pay_use, params WHERE month = date_trunc('month', as_of) - INTERVAL 1 MONTH;

-- ------------------------------------------------------------ by contract type
-- @out user_ga_by_contract_monthly
SELECT contract_type, month,
       COUNT(*) FILTER (WHERE act > 0)                                        AS active_orgs,
       COUNT(*) FILTER (WHERE months_since_first = 0 AND act > 0)             AS new_orgs,
       COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev > 0) AS retained_orgs,
       COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev = 0) AS resurrected_orgs,
      -COUNT(*) FILTER (WHERE act = 0 AND act_prev > 0)                       AS churned_orgs,
       ROUND((COUNT(*) FILTER (WHERE months_since_first = 0 AND act > 0) + COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev = 0))
             / NULLIF(COUNT(*) FILTER (WHERE act = 0 AND act_prev > 0), 0)::DOUBLE, 2) AS quick_ratio
FROM (SELECT *, date_diff('month', first_month, month) AS months_since_first FROM usage_panel)
GROUP BY 1, 2 ORDER BY 1, 2;

-- @out user_ga_by_contract_last_12
SELECT contract_type,
       ROUND(AVG(active_orgs)) AS mean_active_orgs, SUM(new_orgs) AS new_orgs_12m, SUM(resurrected_orgs) AS resurrected_12m,
       SUM(churned_orgs) AS churned_12m,
       ROUND((SUM(new_orgs) + SUM(resurrected_orgs)) / NULLIF(-SUM(churned_orgs), 0)::DOUBLE, 2) AS quick_ratio_12m,
       ROUND(100.0 * -SUM(churned_orgs) / SUM(active_orgs), 1) AS monthly_churn_pct
FROM (SELECT contract_type, month,
             COUNT(*) FILTER (WHERE act > 0) AS active_orgs,
             COUNT(*) FILTER (WHERE months_since_first = 0 AND act > 0) AS new_orgs,
             COUNT(*) FILTER (WHERE months_since_first > 0 AND act > 0 AND act_prev = 0) AS resurrected_orgs,
            -COUNT(*) FILTER (WHERE act = 0 AND act_prev > 0) AS churned_orgs
      FROM (SELECT *, date_diff('month', first_month, month) AS months_since_first FROM usage_panel), params
      WHERE month < date_trunc('month', as_of) AND month >= date_trunc('month', as_of) - INTERVAL 12 MONTH
      GROUP BY 1, 2)
GROUP BY 1 ORDER BY 2 DESC;

-- ------------------------------------------------------------ end-user (seat) growth accounting
-- The log carries no user ids, only a daily active-user count per organization, so users
-- cannot be followed individually. What can be followed is each organization's seats in use
-- (peak daily active users in the month), classified the way the toolkit classifies revenue:
--   new         = seats of organizations in their first month
--   retained    = min(this month, last month)
--   expansion   = seats added by organizations that grew
--   contraction = seats lost by organizations that shrank (negative)
--   resurrected = seats of organizations back after a silent month
--   churned     = last month's seats of organizations silent this month (negative)
CREATE OR REPLACE VIEW seat_ga AS
  SELECT contract_type, month,
         SUM(seats)                                                                        AS seats,
         SUM(CASE WHEN months_since_first = 0 THEN seats END)                              AS new_seats,
         SUM(CASE WHEN months_since_first > 0 AND seats > 0 AND seats_prev > 0
                  THEN LEAST(seats, seats_prev) END)                                       AS retained_seats,
         SUM(CASE WHEN months_since_first > 0 AND seats > seats_prev AND seats_prev > 0
                  THEN seats - seats_prev END)                                             AS expansion_seats,
        -SUM(CASE WHEN months_since_first > 0 AND seats > 0 AND seats < seats_prev
                  THEN seats_prev - seats END)                                             AS contraction_seats,
         SUM(CASE WHEN months_since_first > 0 AND seats > 0 AND seats_prev = 0 THEN seats END) AS resurrected_seats,
        -SUM(CASE WHEN seats = 0 AND seats_prev > 0 THEN seats_prev END)                   AS churned_seats
  FROM (SELECT *, date_diff('month', first_month, month) AS months_since_first FROM usage_panel)
  GROUP BY 1, 2;

-- @out seat_ga_monthly
SELECT month, SUM(seats) AS seats, SUM(new_seats) AS new_seats, SUM(retained_seats) AS retained_seats,
       SUM(expansion_seats) AS expansion_seats, SUM(contraction_seats) AS contraction_seats,
       SUM(resurrected_seats) AS resurrected_seats, SUM(churned_seats) AS churned_seats,
       ROUND((COALESCE(SUM(new_seats), 0) + COALESCE(SUM(resurrected_seats), 0) + COALESCE(SUM(expansion_seats), 0))
             / NULLIF(-(COALESCE(SUM(churned_seats), 0) + COALESCE(SUM(contraction_seats), 0)), 0)::DOUBLE, 2) AS quick_ratio
FROM seat_ga GROUP BY 1 ORDER BY 1;

-- @out seat_ga_by_contract_monthly
SELECT contract_type, month, seats, new_seats, retained_seats, expansion_seats, contraction_seats, resurrected_seats, churned_seats,
       ROUND((COALESCE(new_seats,0) + COALESCE(resurrected_seats,0) + COALESCE(expansion_seats,0))
             / NULLIF(-(COALESCE(churned_seats,0) + COALESCE(contraction_seats,0)), 0)::DOUBLE, 2) AS quick_ratio
FROM seat_ga ORDER BY contract_type, month;

-- @out seat_ga_by_contract_last_12
SELECT contract_type, ROUND(AVG(seats)) AS mean_seats,
       ROUND(100.0 * SUM(new_seats) / SUM(seats), 1) AS new_pct,
       ROUND(100.0 * SUM(expansion_seats) / SUM(seats), 1) AS expansion_pct,
       ROUND(100.0 * SUM(contraction_seats) / SUM(seats), 1) AS contraction_pct,
       ROUND(100.0 * SUM(churned_seats) / SUM(seats), 1) AS churned_pct,
       ROUND((COALESCE(SUM(new_seats), 0) + COALESCE(SUM(resurrected_seats), 0) + COALESCE(SUM(expansion_seats), 0))
             / NULLIF(-(COALESCE(SUM(churned_seats), 0) + COALESCE(SUM(contraction_seats), 0)), 0)::DOUBLE, 2) AS quick_ratio_12m
FROM seat_ga, params
WHERE month < date_trunc('month', as_of) AND month >= date_trunc('month', as_of) - INTERVAL 12 MONTH
GROUP BY 1 ORDER BY 2 DESC;
