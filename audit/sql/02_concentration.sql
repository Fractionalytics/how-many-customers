-- 02_concentration.sql : concentration first, because revenue resting on a few customers is
-- a risk the multiple should price. Computed from the invoices, then again from the CRM, and
-- the two do not agree because there is no shared key and mrr_usd is a separate number.

-- Trailing twelve months of paid cash by billing customer.
CREATE OR REPLACE VIEW ttm_by_customer AS
  SELECT customer_ref, parent_k, contract_type, SUM(amount_usd) AS ttm
  FROM inv_paid, params
  WHERE invoice_date > as_of - INTERVAL 365 DAY
  GROUP BY 1, 2, 3;

-- @out ttm_totals
SELECT COUNT(*) AS paying_customers, COUNT(DISTINCT parent_k) AS paying_entities,
       ROUND(SUM(ttm)) AS ttm_paid_usd, ROUND(AVG(ttm)) AS mean_ttm, ROUND(MEDIAN(ttm)) AS median_ttm,
       ROUND(MAX(ttm)) AS largest_customer
FROM ttm_by_customer;

-- Top-N share, billing customer_ref grain and parent-entity grain side by side.
-- @out top_n_share
WITH byref AS (
  SELECT ttm, ROW_NUMBER() OVER (ORDER BY ttm DESC) AS rn, SUM(ttm) OVER () AS total FROM ttm_by_customer),
byent AS (
  SELECT ttm, ROW_NUMBER() OVER (ORDER BY ttm DESC) AS rn, SUM(ttm) OVER () AS total
  FROM (SELECT parent_k, SUM(ttm) AS ttm FROM ttm_by_customer GROUP BY 1)),
n AS (SELECT * FROM (VALUES (1),(5),(10),(20),(50),(100)) t(top_n))
SELECT n.top_n,
       ROUND(100.0 * (SELECT SUM(ttm) FROM byref WHERE rn <= n.top_n) / (SELECT MAX(total) FROM byref), 1) AS share_by_customer_ref_pct,
       ROUND(100.0 * (SELECT SUM(ttm) FROM byent WHERE rn <= n.top_n) / (SELECT MAX(total) FROM byent), 1) AS share_by_parent_entity_pct
FROM n ORDER BY 1;

-- Lorenz curve points: cumulative revenue share by customer percentile (for the chart).
-- @out lorenz_curve
WITH ranked AS (
  SELECT ttm, ROW_NUMBER() OVER (ORDER BY ttm DESC) AS rn, COUNT(*) OVER () AS n, SUM(ttm) OVER () AS total
  FROM ttm_by_customer)
SELECT pct AS top_pct_of_customers,
       ROUND(100.0 * SUM(ttm) FILTER (WHERE rn <= CEIL(n * pct / 100.0)) / MAX(total), 1) AS revenue_share_pct
FROM ranked, (SELECT * FROM (VALUES (1),(2),(5),(10),(20),(30),(40),(50),(60),(70),(80),(90),(100)) t(pct))
GROUP BY pct ORDER BY pct;

-- Herfindahl-Hirschman index on revenue share (10,000 = one customer), and the effective
-- number of customers it implies.
-- @out hhi
SELECT ROUND(SUM(POWER(100.0 * ttm / total, 2)), 0) AS hhi,
       ROUND(10000.0 / SUM(POWER(100.0 * ttm / total, 2)), 0) AS effective_customer_count
FROM (SELECT ttm, SUM(ttm) OVER () AS total FROM ttm_by_customer);

-- The CRM's version of the same question. Annualized mrr_usd on live accounts.
-- @out concentration_crm_vs_billing
WITH crm_ann AS (
  SELECT mrr_usd * 12 AS arr, ROW_NUMBER() OVER (ORDER BY mrr_usd DESC) AS rn, SUM(mrr_usd * 12) OVER () AS total
  FROM crm WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned'),
b AS (SELECT ttm, ROW_NUMBER() OVER (ORDER BY ttm DESC) AS rn, SUM(ttm) OVER () AS total FROM ttm_by_customer),
n AS (SELECT * FROM (VALUES (1),(5),(10),(20),(50)) t(top_n))
SELECT n.top_n,
       ROUND(100.0 * (SELECT SUM(ttm) FROM b WHERE rn <= n.top_n) / (SELECT MAX(total) FROM b), 1) AS billing_ttm_share_pct,
       ROUND(100.0 * (SELECT SUM(arr) FROM crm_ann WHERE rn <= n.top_n) / (SELECT MAX(total) FROM crm_ann), 1) AS crm_annualized_share_pct
FROM n ORDER BY 1;

-- @out revenue_base_by_system
SELECT 'billing, paid cash, TTM' AS basis, ROUND(SUM(ttm)) AS usd, COUNT(*) AS customers FROM ttm_by_customer
UNION ALL SELECT 'billing, recognized, TTM', ROUND(SUM(rev)), COUNT(DISTINCT customer_ref) FROM rev_amort, params
  WHERE month > date_trunc('month', as_of) - INTERVAL 12 MONTH AND month <= date_trunc('month', as_of)
UNION ALL SELECT 'CRM, Active x mrr_usd x 12', ROUND(SUM(mrr_usd) * 12), COUNT(*) FROM crm WHERE account_status = 'Active'
UNION ALL SELECT 'CRM, not Churned and mrr > 0, x 12', ROUND(SUM(mrr_usd) * 12), COUNT(*) FROM crm WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned';

-- Concentration by contract type: where does the top decile sit?
-- @out top_decile_by_contract
WITH ranked AS (SELECT *, NTILE(10) OVER (ORDER BY ttm DESC) AS decile FROM ttm_by_customer)
SELECT contract_type,
       COUNT(*) AS customers,
       COUNT(*) FILTER (WHERE decile = 1) AS in_top_decile,
       ROUND(100.0 * SUM(ttm) / (SELECT SUM(ttm) FROM ttm_by_customer), 1) AS revenue_share_pct
FROM ranked GROUP BY 1 ORDER BY 4 DESC;

-- The largest customers, named, as an acquirer would want them.
-- @out top_10_customers
SELECT b.company_name, t.contract_type, ROUND(t.ttm) AS ttm_usd,
       ROUND(100.0 * t.ttm / SUM(t.ttm) OVER (), 2) AS share_pct,
       ROUND(100.0 * SUM(t.ttm) OVER (ORDER BY t.ttm DESC ROWS UNBOUNDED PRECEDING) / SUM(t.ttm) OVER (), 1) AS cum_share_pct
FROM ttm_by_customer t JOIN bill b USING (customer_ref)
ORDER BY t.ttm DESC LIMIT 10;
