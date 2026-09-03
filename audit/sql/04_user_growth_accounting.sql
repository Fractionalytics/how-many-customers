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
