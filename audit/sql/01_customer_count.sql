-- 01_customer_count.sql : how many customers? Every rule is defensible. They disagree.
-- The growth-accounting count (monthly active orgs from telemetry) is added as another source.

-- @out count_rules
WITH p AS (SELECT as_of FROM params),
r AS (
  SELECT 1 AS ord, 'CRM account_status = Active (rows)' AS rule, COUNT(*) AS n
    FROM crm WHERE account_status = 'Active'
  UNION ALL SELECT 2, 'CRM account_status = Active (distinct name key)', COUNT(DISTINCT k)
    FROM crm_keyed WHERE account_status = 'Active'
  UNION ALL SELECT 3, 'CRM mrr_usd > 0 and not Churned (rows)', COUNT(*)
    FROM crm WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned'
  UNION ALL SELECT 4, 'CRM mrr_usd > 0 and not Churned (distinct name key)', COUNT(DISTINCT k)
    FROM crm_keyed WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned'
  UNION ALL SELECT 5, 'Billing: paid invoice in last 90 days (customer_ref)', COUNT(DISTINCT customer_ref)
    FROM inv, p WHERE status = 'paid' AND invoice_date >= as_of - INTERVAL 90 DAY
  UNION ALL SELECT 6, 'Billing: paid invoice in last 90 days (parent entity)', COUNT(DISTINCT parent_k)
    FROM inv_paid, p WHERE invoice_date >= as_of - INTERVAL 90 DAY
  UNION ALL SELECT 7, 'Billing: paid invoice in last 365 days (customer_ref)', COUNT(DISTINCT customer_ref)
    FROM inv, p WHERE status = 'paid' AND invoice_date >= as_of - INTERVAL 365 DAY
  UNION ALL SELECT 8, 'Billing: contract-aware (monthly/usage paid 90d, annual paid 365d)', COUNT(DISTINCT customer_ref)
    FROM inv_paid, p
    WHERE invoice_date >= as_of - INTERVAL 90 DAY
       OR (contract_type = 'annual' AND invoice_date >= as_of - INTERVAL 365 DAY)
  UNION ALL SELECT 9, 'Billing: recognized revenue > 0 in the as-of month', COUNT(DISTINCT customer_ref)
    FROM rev_amort, p WHERE month = date_trunc('month', as_of) AND rev > 0
  UNION ALL SELECT 10, 'Product: any usage in last 30 days (org_slug)', COUNT(DISTINCT org_slug)
    FROM usage, p WHERE event_date >= as_of - INTERVAL 30 DAY
  UNION ALL SELECT 11, 'Product: monthly active orgs, last complete month', COUNT(DISTINCT org_slug)
    FROM usage_month, p WHERE month = date_trunc('month', as_of) - INTERVAL 1 MONTH
)
SELECT ord, rule, n FROM r ORDER BY ord;

-- @out count_spread
WITH r AS (
  SELECT COUNT(*) AS n FROM crm WHERE account_status = 'Active'
  UNION ALL SELECT COUNT(DISTINCT customer_ref) FROM inv, params WHERE status='paid' AND invoice_date >= as_of - INTERVAL 90 DAY
  UNION ALL SELECT COUNT(DISTINCT org_slug) FROM usage, params WHERE event_date >= as_of - INTERVAL 30 DAY
  UNION ALL SELECT COUNT(*) FROM crm WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned'
)
SELECT MIN(n) AS lowest, MAX(n) AS highest, MAX(n) - MIN(n) AS spread,
       ROUND(100.0 * (MAX(n) - MIN(n)) / MIN(n), 1) AS spread_pct_of_lowest
FROM r;

-- Why the 90-day rule is the trap: annual customers who are current and last paid > 90d ago.
-- @out annual_invisible_to_90d
SELECT contract_type,
       COUNT(*) AS billing_customers,
       COUNT(*) FILTER (WHERE last_paid_invoice_date < as_of - INTERVAL 90 DAY) AS last_paid_over_90d_ago,
       COUNT(*) FILTER (WHERE last_paid_invoice_date >= as_of - INTERVAL 365 DAY
                          AND last_paid_invoice_date <  as_of - INTERVAL 90 DAY) AS paid_91_to_365d_ago
FROM bill, params GROUP BY 1 ORDER BY 2 DESC;

-- The same fork one level down: is the window boundary inclusive? Nobody writes this down either.
-- @out boundary_inclusive_vs_exclusive
SELECT 'paid 90d, >= boundary' AS rule, COUNT(DISTINCT customer_ref) AS n FROM inv, params WHERE status='paid' AND invoice_date >= as_of - INTERVAL 90 DAY
UNION ALL SELECT 'paid 90d, >  boundary', COUNT(DISTINCT customer_ref) FROM inv, params WHERE status='paid' AND invoice_date >  as_of - INTERVAL 90 DAY
UNION ALL SELECT 'usage 30d, >= boundary', COUNT(DISTINCT org_slug) FROM usage, params WHERE event_date >= as_of - INTERVAL 30 DAY
UNION ALL SELECT 'usage 30d, >  boundary', COUNT(DISTINCT org_slug) FROM usage, params WHERE event_date >  as_of - INTERVAL 30 DAY;

-- Status picklist, with blank kept separate from Inactive (trap 11).
-- @out crm_status_picklist
SELECT COALESCE(NULLIF(account_status, ''), '(blank)') AS account_status, COUNT(*) AS rows,
       ROUND(AVG(mrr_usd), 0) AS avg_mrr, COUNT(*) FILTER (WHERE mrr_usd > 0) AS with_mrr
FROM crm GROUP BY 1 ORDER BY 2 DESC;
