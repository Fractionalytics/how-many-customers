-- 07_segments.sql : the segments carrying the thesis, named and tested.
-- Working thesis for this book: (1) annual mid-market contracts drive retention and expansion;
-- (2) the acquired books retain as well as the organic ones.
-- Contract type lives in billing. Sector, plan tier and owner live in the CRM, so every CRM
-- segment reaches revenue only through the name bridge, and its coverage is stated first.

-- @out bridge_coverage
SELECT (SELECT COUNT(*) FROM bill) AS billing_customers,
       (SELECT COUNT(*) FROM bridge WHERE tier = 1) AS matched_tier1_exact,
       (SELECT COUNT(*) FROM bridge WHERE tier = 2) AS matched_tier2_stem,
       ROUND(100.0 * (SELECT COUNT(*) FROM bridge) / (SELECT COUNT(*) FROM bill), 1) AS match_pct,
       (SELECT COUNT(*) FROM crm) AS crm_accounts,
       (SELECT COUNT(DISTINCT account_id) FROM bridge) AS crm_accounts_matched,
       (SELECT ROUND(100.0 * SUM(ttm) FILTER (WHERE customer_ref IN (SELECT customer_ref FROM bridge)) / SUM(ttm), 1) FROM ttm_by_customer) AS ttm_revenue_covered_pct;

-- A customer-level segment table: billing grain, CRM attributes attached where the bridge holds.
CREATE OR REPLACE VIEW seg AS
  SELECT b.customer_ref, b.contract_type, t.ttm, br.tier,
         c.sector, c.plan_tier, c.owner, c.mrr_usd AS crm_mrr, c.account_status
  FROM bill_keyed b
  LEFT JOIN ttm_by_customer t USING (customer_ref)
  LEFT JOIN bridge br USING (customer_ref)
  LEFT JOIN crm c USING (account_id);

-- Twelve-month logo retention and NRR per customer segment, base months in the last 24 months.
CREATE OR REPLACE MACRO seg_retention(col) AS TABLE
  SELECT COALESCE(col::VARCHAR, '(unmatched)') AS segment,
         COUNT(DISTINCT a.customer_ref) AS customers_in_base,
         ROUND(100.0 * COUNT(*) FILTER (WHERE b.rev > 0) / COUNT(*), 1) AS logo_retention_12m_pct,
         ROUND(100.0 * SUM(b.rev) / SUM(a.rev), 1) AS nrr_12m_pct,
         ROUND(100.0 * SUM(LEAST(a.rev, b.rev)) / SUM(a.rev), 1) AS grr_12m_pct
  FROM panel a
  JOIN panel b ON b.customer_ref = a.customer_ref AND b.month = (a.month + INTERVAL 12 MONTH)::DATE
  JOIN seg s ON s.customer_ref = a.customer_ref, params
  WHERE a.rev > 0 AND (a.month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
    AND a.month >= date_trunc('month', as_of) - INTERVAL 24 MONTH
  GROUP BY 1 ORDER BY 2 DESC;

-- @out retention_by_contract_type
SELECT * FROM seg_retention(contract_type);

-- @out retention_by_plan_tier
SELECT * FROM seg_retention(plan_tier);

-- @out retention_by_sector
SELECT * FROM seg_retention(sector);

-- @out retention_by_owner
SELECT * FROM seg_retention(owner);

-- Revenue and concentration by segment.
CREATE OR REPLACE MACRO seg_revenue(col) AS TABLE
  SELECT COALESCE(col::VARCHAR, '(unmatched)') AS segment,
         COUNT(*) FILTER (WHERE ttm > 0) AS paying_customers,
         ROUND(SUM(ttm)) AS ttm_usd,
         ROUND(100.0 * SUM(ttm) / (SELECT SUM(ttm) FROM seg), 1) AS revenue_share_pct,
         ROUND(AVG(ttm) FILTER (WHERE ttm > 0)) AS mean_ttm_per_paying,
         ROUND(MEDIAN(ttm) FILTER (WHERE ttm > 0)) AS median_ttm_per_paying
  FROM seg GROUP BY 1 ORDER BY 3 DESC;

-- @out revenue_by_contract_type
SELECT * FROM seg_revenue(contract_type);

-- @out revenue_by_sector
SELECT * FROM seg_revenue(sector);

-- @out revenue_by_plan_tier
SELECT * FROM seg_revenue(plan_tier);

-- @out revenue_by_owner
SELECT * FROM seg_revenue(owner);

-- Does plan_tier mean anything? If tier does not predict MRR, the field is not maintained.
-- @out plan_tier_vs_mrr
SELECT plan_tier, COUNT(*) AS accounts, ROUND(AVG(mrr_usd)) AS mean_mrr, ROUND(MEDIAN(mrr_usd)) AS median_mrr,
       ROUND(QUANTILE_CONT(mrr_usd, 0.9)) AS p90_mrr
FROM crm WHERE mrr_usd > 0 GROUP BY 1 ORDER BY 3 DESC;

-- Thesis leg 2, the acquired books: no field identifies them. The test that would find a bought
-- list (a signing-date spike) is in 06; here, the CRM created_date histogram by quarter for the chart.
-- @out crm_accounts_created_by_quarter
SELECT date_trunc('quarter', created_date)::DATE AS quarter, COUNT(*) AS accounts_created,
       COUNT(*) FILTER (WHERE lead_source IS NULL OR lead_source = '') AS lead_source_blank
FROM crm GROUP BY 1 ORDER BY 1;

-- ------------------------------------------------------------------ thesis leg 2, with the schedules
-- The acquisition schedules the seller produced on request, joined to billing through the same
-- name key. (Empty when the company carries no acquisition_schedules.csv.)

CREATE OR REPLACE VIEW acquired AS
  SELECT s.book, s.closed, s.customer, s.original_contract_date, b.customer_ref
  FROM schedules s
  LEFT JOIN bill_keyed b ON b.parent_k = canon_key(s.customer);

-- @out acquired_schedule_match
SELECT book, closed, COUNT(*) AS accounts_on_schedule,
       COUNT(customer_ref) AS matched_to_billing,
       ROUND(100.0 * COUNT(customer_ref) / COUNT(*), 1) AS match_pct
FROM acquired GROUP BY 1, 2 ORDER BY 2;

-- Twelve-month retention: acquired versus organic, base months in the last 24 months.
-- @out retention_acquired_vs_organic
WITH tag AS (
  SELECT b.customer_ref, COALESCE(a.book, 'organic') AS origin FROM bill b LEFT JOIN acquired a USING (customer_ref))
SELECT t.origin AS segment,
       COUNT(DISTINCT a.customer_ref) AS customers_in_base,
       ROUND(100.0 * COUNT(*) FILTER (WHERE b.rev > 0) / COUNT(*), 1) AS logo_retention_12m_pct,
       ROUND(100.0 * SUM(b.rev) / SUM(a.rev), 1) AS nrr_12m_pct,
       ROUND(100.0 * SUM(LEAST(a.rev, b.rev)) / SUM(a.rev), 1) AS grr_12m_pct
FROM panel a
JOIN panel b ON b.customer_ref = a.customer_ref AND b.month = (a.month + INTERVAL 12 MONTH)::DATE
JOIN tag t ON t.customer_ref = a.customer_ref, params
WHERE a.rev > 0 AND (a.month + INTERVAL 12 MONTH)::DATE < date_trunc('month', as_of)
  AND a.month >= date_trunc('month', as_of) - INTERVAL 24 MONTH
GROUP BY 1 ORDER BY 2 DESC;

-- The fingerprint a bought book leaves in billing: first invoices bunch in the quarter after close.
-- @out new_billing_customers_by_quarter_vs_closes
WITH q AS (
  SELECT date_trunc('quarter', first_month)::DATE AS quarter, COUNT(*) AS new_billing_customers
  FROM (SELECT customer_ref, MIN(month) AS first_month FROM rev_amort GROUP BY 1) GROUP BY 1)
SELECT q.quarter, q.new_billing_customers,
       (SELECT STRING_AGG(DISTINCT book || ' closed ' || closed, '; ') FROM schedules s
         WHERE date_trunc('quarter', s.closed)::DATE = q.quarter
            OR date_trunc('quarter', s.closed + INTERVAL 1 MONTH)::DATE = q.quarter) AS acquisition_closes_nearby
FROM q ORDER BY 1;

-- CRM created_date against billing first invoice: a migrated book shows years of gap.
-- @out crm_created_vs_first_invoice_gap
SELECT CASE WHEN gap_days < 60 THEN 'under 60 days'
            WHEN gap_days < 365 THEN '60 days to 1 year'
            WHEN gap_days < 1095 THEN '1 to 3 years'
            ELSE 'over 3 years' END AS crm_created_before_first_invoice_by,
       COUNT(*) AS billing_customers, ROUND(SUM(t.ttm)) AS ttm_usd
FROM (SELECT b.customer_ref, date_diff('day', c.created_date, b.first_invoice_date) AS gap_days
      FROM bill b JOIN bridge br USING (customer_ref) JOIN crm c USING (account_id)) g
LEFT JOIN ttm_by_customer t USING (customer_ref)
GROUP BY 1 ORDER BY MIN(gap_days);

-- The mix shift, as the audit sees it: new billing customers per quarter by CRM plan tier.
-- @out new_customers_by_quarter_and_tier
SELECT date_trunc('quarter', f.first_month)::DATE AS quarter, COALESCE(c.plan_tier, '(unmatched)') AS plan_tier, COUNT(*) AS new_customers
FROM (SELECT customer_ref, MIN(month) AS first_month FROM rev_amort GROUP BY 1) f
LEFT JOIN bridge br USING (customer_ref) LEFT JOIN crm c USING (account_id)
GROUP BY 1, 2 ORDER BY 1, 2;
