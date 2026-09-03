-- 06_clv_payback.sql : lifetime value, acquisition cost, and payback. Every one of them divides
-- by, or groups by, a customer count that nobody has agreed on, and payback also fractures on
-- contract type.

-- Observed lifetime revenue per billing customer (paid cash, whole history).
-- @out lifetime_revenue_per_customer
SELECT contract_type, COUNT(*) AS customers,
       ROUND(AVG(life)) AS mean_lifetime_usd, ROUND(MEDIAN(life)) AS median_lifetime_usd,
       ROUND(AVG(life) / MEDIAN(life), 2) AS mean_over_median,
       ROUND(AVG(months_paying), 1) AS mean_months_with_revenue
FROM (SELECT customer_ref, contract_type, SUM(amount_usd) AS life, COUNT(DISTINCT inv_month) AS months_paying
      FROM inv_paid GROUP BY 1, 2)
GROUP BY ROLLUP (contract_type) ORDER BY contract_type NULLS FIRST;

-- Cumulative recognized revenue per cohort customer at fixed tenure, all cohorts old enough.
-- This is the observed CLV curve; nothing here is projected.
-- @out cum_revenue_per_customer_by_tenure
SELECT k AS months_since_first,
       COUNT(DISTINCT cohort) AS cohorts_reaching_k, SUM(cohort_size) AS customers,
       ROUND(SUM(cum_rev_per_cohort_customer * cohort_size) / SUM(cohort_size)) AS cum_rev_per_customer_usd
FROM cohort_long WHERE k IN (0, 3, 6, 12, 18, 24, 30, 36, 42)
GROUP BY 1 ORDER BY 1;

-- ------------------------------------------------------------------ CAC
-- Monthly spend, all channels.
CREATE OR REPLACE VIEW spend_month AS
  SELECT (month || '-01')::DATE AS month, SUM(spend_usd) AS spend FROM spend GROUP BY 1;

-- New customers per month under two counts: first paid invoice (billing) and CRM created_date.
CREATE OR REPLACE VIEW new_per_month AS
  SELECT m.month,
         (SELECT COUNT(*) FROM (SELECT customer_ref, MIN(month) AS f FROM rev_amort GROUP BY 1) WHERE f = m.month) AS new_billing,
         (SELECT COUNT(*) FROM crm WHERE date_trunc('month', created_date) = m.month) AS new_crm_rows
  FROM months m;

-- Cohort CAC: spend in the month, lagged by one (spend leads signup), over the new customers.
-- @out cac_by_quarter_two_denominators
WITH q AS (
  SELECT date_trunc('quarter', n.month)::DATE AS quarter,
         SUM(s.spend) AS spend, SUM(n.new_billing) AS new_billing, SUM(n.new_crm_rows) AS new_crm_rows
  FROM new_per_month n JOIN spend_month s ON s.month = (n.month - INTERVAL 1 MONTH)::DATE
  GROUP BY 1)
SELECT quarter, ROUND(spend) AS spend_lagged_1m, new_billing, new_crm_rows,
       ROUND(spend / NULLIF(new_billing, 0)) AS cac_per_billing_customer,
       ROUND(spend / NULLIF(new_crm_rows, 0)) AS cac_per_crm_account,
       ROUND(100.0 * (spend / NULLIF(new_crm_rows, 0)) / (spend / NULLIF(new_billing, 0)) - 100, 1) AS gap_pct
FROM q, params WHERE quarter < date_trunc('quarter', as_of) ORDER BY quarter;

-- Blended CAC over the whole history, with every count rule as the denominator.
-- CAVEAT, and say it out loud: this divides 47 months of cumulative spend by a point-in-time
-- customer count. It is here to isolate the denominator, and the error is the lesson: a
-- lifetime numerator over a snapshot denominator is the single most common way CAC gets
-- misreported. The defensible form is the cohort CAC above, and it still needs the definition.
-- @out cac_by_count_rule
WITH s AS (SELECT SUM(spend_usd) AS spend FROM spend),
r AS (
  SELECT 'CRM Active (rows)' AS rule, COUNT(*) AS n FROM crm WHERE account_status = 'Active'
  UNION ALL SELECT 'product usage 30d', COUNT(DISTINCT org_slug) FROM usage, params WHERE event_date >= as_of - INTERVAL 30 DAY
  UNION ALL SELECT 'CRM mrr > 0 not Churned', COUNT(*) FROM crm WHERE mrr_usd > 0 AND COALESCE(account_status,'') <> 'Churned'
  UNION ALL SELECT 'paid invoice 90d', COUNT(DISTINCT customer_ref) FROM inv, params WHERE status='paid' AND invoice_date >= as_of - INTERVAL 90 DAY
  UNION ALL SELECT 'contract-aware billing', COUNT(DISTINCT customer_ref) FROM inv_paid, params
    WHERE invoice_date >= as_of - INTERVAL 90 DAY OR (contract_type='annual' AND invoice_date >= as_of - INTERVAL 365 DAY)
  UNION ALL SELECT 'all billing customers ever', COUNT(*) FROM bill
  UNION ALL SELECT 'all CRM accounts ever', COUNT(*) FROM crm)
SELECT rule, n, ROUND(spend / n) AS cumulative_spend_over_count FROM r, s ORDER BY n DESC;

-- ------------------------------------------------------------------ payback
-- Cohort payback: months until cumulative recognized revenue per cohort customer covers the
-- cohort's CAC (lagged spend over new billing customers in the cohort quarter).
-- @out payback_by_cohort_quarter
WITH cac AS (
  SELECT date_trunc('quarter', n.month)::DATE AS quarter, SUM(s.spend) / NULLIF(SUM(n.new_billing), 0) AS cac
  FROM new_per_month n JOIN spend_month s ON s.month = (n.month - INTERVAL 1 MONTH)::DATE GROUP BY 1),
curve AS (
  SELECT date_trunc('quarter', cohort)::DATE AS quarter, k,
         SUM(cum_rev_per_cohort_customer * cohort_size) / SUM(cohort_size) AS cum_per_cust
  FROM cohort_long GROUP BY 1, 2),
hit AS (
  SELECT c.quarter, MIN(k) AS payback_months
  FROM curve c JOIN cac USING (quarter) WHERE cum_per_cust >= cac GROUP BY 1)
SELECT cac.quarter, ROUND(cac.cac) AS cac_usd,
       ROUND((SELECT cum_per_cust FROM curve WHERE curve.quarter = cac.quarter AND k = 12)) AS cum_rev_12m_per_customer,
       (SELECT MAX(k) FROM curve WHERE curve.quarter = cac.quarter) AS months_observed,
       hit.payback_months
FROM cac LEFT JOIN hit USING (quarter), params
WHERE cac.quarter < date_trunc('quarter', as_of) - INTERVAL 3 MONTH
ORDER BY cac.quarter;

-- Payback fractures on contract type: an annual customer pays twelve months up front.
-- @out payback_by_contract_type_cash_vs_recognized
WITH cac AS (
  SELECT SUM(s.spend) / NULLIF(SUM(n.new_billing), 0) AS cac
  FROM new_per_month n JOIN spend_month s ON s.month = (n.month - INTERVAL 1 MONTH)::DATE, params
  WHERE n.month >= date_trunc('month', as_of) - INTERVAL 24 MONTH AND n.month < date_trunc('month', as_of) - INTERVAL 12 MONTH),
first_month_cash AS (
  SELECT b.contract_type, AVG(rev) AS month0_cash
  FROM panel_cash p JOIN bill_keyed b USING (customer_ref) WHERE months_since_first = 0 GROUP BY 1),
monthly_rec AS (
  SELECT b.contract_type, AVG(rev) AS avg_monthly_recognized
  FROM panel p JOIN bill_keyed b USING (customer_ref) WHERE months_since_first BETWEEN 0 AND 11 AND rev > 0 GROUP BY 1)
SELECT f.contract_type, ROUND(cac.cac) AS blended_cac_usd,
       ROUND(f.month0_cash) AS first_month_cash_usd,
       ROUND(m.avg_monthly_recognized) AS avg_monthly_recognized_usd,
       ROUND(cac.cac / f.month0_cash, 1) AS payback_months_on_cash,
       ROUND(cac.cac / m.avg_monthly_recognized, 1) AS payback_months_recognized
FROM first_month_cash f JOIN monthly_rec m USING (contract_type), cac ORDER BY 1;

-- ------------------------------------------------- CAC by channel: not computable
-- @out channel_vocabulary_finance_vs_crm
SELECT 'finance (marketing_spend.channel)' AS system, COUNT(DISTINCT channel) AS distinct_values, STRING_AGG(DISTINCT channel, ' | ' ORDER BY channel) AS values FROM spend
UNION ALL
SELECT 'sales (crm_accounts.lead_source), non-blank', COUNT(DISTINCT lead_source), STRING_AGG(DISTINCT lead_source, ' | ' ORDER BY lead_source)
FROM crm WHERE lead_source IS NOT NULL AND lead_source <> '';

-- @out lead_source_blank_by_tenure
SELECT CASE WHEN created_date < DATE '2024-06-01' THEN 'created before 2024-06-01 (field did not exist)' ELSE 'created on/after 2024-06-01' END AS era,
       COUNT(*) AS rows,
       COUNT(*) FILTER (WHERE lead_source IS NULL OR lead_source = '') AS blank,
       ROUND(100.0 * COUNT(*) FILTER (WHERE lead_source IS NULL OR lead_source = '') / COUNT(*), 1) AS blank_pct,
       ROUND(AVG(mrr_usd)) AS avg_mrr
FROM crm GROUP BY 1 ORDER BY 1;

-- @out spend_rows_with_an_account_key
SELECT COUNT(*) AS spend_rows,
       COUNT(*) FILTER (WHERE FALSE) AS rows_with_account_id_or_customer_ref_or_org_slug
FROM spend;

-- The acquired book: nothing in any file flags it. The obvious tell, a creation-date spike, is absent.
-- @out acquired_book_spike_test
WITH m AS (SELECT date_trunc('month', created_date)::DATE AS month, COUNT(*) AS n FROM crm GROUP BY 1)
SELECT ROUND(MEDIAN(n), 1) AS median_accounts_per_month, MAX(n) AS max_month,
       ROUND(MAX(n) / MEDIAN(n), 2) AS max_over_median,
       COUNT(*) FILTER (WHERE n > 1.8 * (SELECT MEDIAN(n) FROM m)) AS months_over_1_8x_median
FROM m;
