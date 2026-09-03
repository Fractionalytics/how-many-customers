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
