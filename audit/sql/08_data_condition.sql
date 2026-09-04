-- 08_data_condition.sql : which reported numbers come from a system, and which get rebuilt by
-- hand. The inventory of the data's condition, as counts.

-- @out systems_and_keys
SELECT 'crm_accounts' AS file, 'account_id' AS primary_key, COUNT(*) AS rows, COUNT(DISTINCT account_id) AS distinct_pk,
       COUNT(DISTINCT k) AS distinct_name_keys, 'none shared with any other file' AS shared_key FROM crm_keyed
UNION ALL SELECT 'billing_customers', 'customer_ref', COUNT(*), COUNT(DISTINCT customer_ref), COUNT(DISTINCT parent_k), 'none' FROM bill_keyed
UNION ALL SELECT 'billing_invoices', 'invoice_id', COUNT(*), COUNT(DISTINCT invoice_id), COUNT(DISTINCT customer_ref), 'customer_ref -> billing_customers' FROM inv
UNION ALL SELECT 'product_usage', '(org_slug, event_date)', COUNT(*), COUNT(DISTINCT org_slug || event_date), COUNT(DISTINCT org_slug), 'none' FROM usage
UNION ALL SELECT 'marketing_spend', '(month, channel)', COUNT(*), COUNT(DISTINCT month || channel), COUNT(DISTINCT channel), 'none: no account key at all' FROM spend;

-- The key that looks like a key: email_domain.
-- @out email_domain_cardinality
WITH d AS (SELECT email_domain, COUNT(*) AS n FROM crm GROUP BY 1)
SELECT (SELECT COUNT(*) FROM crm) AS crm_rows, COUNT(*) AS distinct_domains,
       MAX(n) AS companies_on_the_busiest_domain,
       (SELECT email_domain FROM d ORDER BY n DESC LIMIT 1) AS busiest_domain
FROM d;

-- Duplicates: the primary-key check passes; the entity check does not.
-- @out duplicates_pk_vs_entity
SELECT 'crm: rows sharing an account_id' AS check_, COUNT(*) FILTER (WHERE n > 1) AS groups, SUM(n - 1) FILTER (WHERE n > 1) AS surplus_rows
FROM (SELECT account_id, COUNT(*) AS n FROM crm GROUP BY 1)
UNION ALL SELECT 'crm: rows sharing a folded name key', COUNT(*) FILTER (WHERE n > 1), SUM(n - 1) FILTER (WHERE n > 1)
FROM (SELECT k, COUNT(*) AS n FROM crm_keyed GROUP BY 1)
UNION ALL SELECT 'billing: customer_refs sharing a parent key (subsidiaries)', COUNT(*) FILTER (WHERE n > 1), SUM(n - 1) FILTER (WHERE n > 1)
FROM (SELECT parent_k, COUNT(*) AS n FROM bill_keyed GROUP BY 1);

-- Coverage between systems, through the entity resolver.
-- @out coverage_between_systems
SELECT 'billing customers with no CRM match (after both tiers)' AS gap, COUNT(*) AS n FROM bill WHERE customer_ref NOT IN (SELECT customer_ref FROM bridge)
UNION ALL SELECT 'CRM accounts with no billing match (after both tiers)', COUNT(*) FROM crm WHERE account_id NOT IN (SELECT account_id FROM bridge_all)
UNION ALL SELECT 'billing customers never invoiced', COUNT(*) FROM bill WHERE customer_ref NOT IN (SELECT customer_ref FROM inv)
UNION ALL SELECT 'usage orgs with no billing match', COUNT(DISTINCT org_slug) FROM usage_month WHERE entity_k NOT IN (SELECT entity_k FROM bill_entity)
UNION ALL SELECT 'usage orgs with no CRM match', COUNT(DISTINCT org_slug) FROM usage_month WHERE entity_k NOT IN (SELECT ck FROM crm_keyed)
UNION ALL SELECT 'invoices whose customer_ref is not in billing_customers', COUNT(*) FROM inv WHERE customer_ref NOT IN (SELECT customer_ref FROM bill);

-- The stems tier 2 refused because they were ambiguous: different companies one token apart.
-- @out ambiguous_stems_left_unmatched
WITH bu AS (SELECT * FROM bill_keyed WHERE customer_ref NOT IN (SELECT customer_ref FROM bridge) AND n_words = 2)
SELECT bu.parent_name AS billing_name, COUNT(DISTINCT c.ck) AS crm_companies_sharing_the_stem,
       STRING_AGG(DISTINCT c.account_name, ' | ' ORDER BY c.account_name) AS candidates
FROM bu JOIN crm_keyed c ON c.stem = bu.stem
GROUP BY 1 HAVING COUNT(DISTINCT c.ck) > 1 ORDER BY 2 DESC LIMIT 12;

-- Telemetry that predates the contract: usage more than 30 days before the first invoice.
-- @out usage_before_first_invoice
WITH first_use AS (SELECT name_key(org_slug) AS k, MIN(event_date) AS first_use FROM usage GROUP BY 1),
     first_bill AS (SELECT e.entity_k AS k, MIN(first_invoice_date) AS first_inv FROM bill b JOIN bill_entity e USING (customer_ref) GROUP BY 1)
SELECT COUNT(*) AS orgs_matched,
       COUNT(*) FILTER (WHERE first_use < first_inv - INTERVAL 30 DAY) AS usage_over_30d_before_first_invoice,
       ROUND(AVG(date_diff('day', first_use, first_inv)) FILTER (WHERE first_use < first_inv - INTERVAL 30 DAY)) AS mean_days_early
FROM first_use JOIN first_bill USING (k);

-- Invoice statuses, and what each does to revenue.
-- @out invoice_status_mix
SELECT status, COUNT(*) AS invoices, ROUND(SUM(amount_usd)) AS usd,
       ROUND(100.0 * SUM(amount_usd) / (SELECT SUM(amount_usd) FROM inv), 1) AS pct_of_gross
FROM inv GROUP BY 1 ORDER BY 2 DESC;

-- Fields with a history. A status that is overwritten in place cannot be audited for any past month.
-- @out fields_with_history
SELECT 'crm.account_status' AS field, 'overwritten in place; no history table' AS condition, 0 AS months_reconstructible
UNION ALL SELECT 'crm.mrr_usd', 'overwritten in place; no history table', 0
UNION ALL SELECT 'crm.lead_source', 'added 2024-06-01; blank before that', (SELECT date_diff('month', DATE '2024-06-01', as_of) FROM params)
UNION ALL SELECT 'billing_invoices', 'append-only ledger', (SELECT date_diff('month', MIN(invoice_date), MAX(invoice_date)) + 1 FROM inv)
UNION ALL SELECT 'product_usage', 'append-only log, retention window', (SELECT date_diff('month', MIN(event_date), MAX(event_date)) + 1 FROM usage)
UNION ALL SELECT 'marketing_spend', 'monthly aggregate, no account link', (SELECT COUNT(DISTINCT month) FROM spend);

-- The reported-number inventory: for each KPI a board would see, which system can produce it
-- and how many defensible values it has in this data.
-- @out kpi_provenance
SELECT * FROM (VALUES
  ('Customer count',        'none: CRM status, billing recency, telemetry each give one',  11, 'rebuilt by hand each month'),
  ('MRR / ARR',             'CRM mrr_usd (hand-entered) or billing recognized (derived)',   4, 'CRM field is typed in; billing needs an amortization rule nobody wrote down'),
  ('TTM revenue',           'billing_invoices',                                              5, 'cash vs recognized vs which statuses count'),
  ('Revenue concentration', 'billing_invoices or CRM mrr_usd',                               2, 'the two systems rank customers differently'),
  ('Logo churn',            'CRM status (no history) or billing panel',                       3, 'CRM cannot say what last month looked like'),
  ('NRR',                   'billing_invoices, recognized basis',                             2, 'cash basis makes annual customers churn and resurrect yearly'),
  ('CAC, blended',          'marketing_spend / a count',                                      7, 'one per count definition'),
  ('CAC by channel',        'not computable',                                                 0, 'no account key on spend; lead_source is last-touch, 23 labels, half blank'),
  ('Payback',               'CAC over cohort revenue',                                        4, 'inherits CAC, then splits on contract type'),
  ('Active users',          'product_usage',                                                  2, 'org vs seat; 13 months of history only')
) t(kpi, system_of_record, defensible_values_found, why_it_is_rebuilt_by_hand);

-- ------------------------------------------------------------------ the board's tab
-- Which reported numbers come from a system, and which get rebuilt by hand. For each month
-- the board saw, the reported figure against what each system can produce for that month.
-- (Empty when the company carries no board_kpis.csv.)

CREATE OR REPLACE VIEW board_vs_systems AS
  WITH b AS (SELECT (month || '-01')::DATE AS month, * EXCLUDE (month) FROM board),
  sys AS (
    SELECT m.month,
           (SELECT COUNT(DISTINCT customer_ref) FROM rev_amort r WHERE r.month = m.month AND r.rev > 0) AS billing_recognized_payers,
           (SELECT COUNT(DISTINCT org_slug) FROM usage_month u WHERE u.month = m.month) AS telemetry_active_orgs,
           (SELECT SUM(rev) FROM rev_amort r WHERE r.month = m.month) AS billing_recognized_rev,
           (SELECT SUM(rev) FROM rev_cash r WHERE r.month = m.month) AS billing_cash_rev,
           (SELECT COUNT(*) FROM (SELECT customer_ref, MIN(month) AS f FROM rev_amort GROUP BY 1) WHERE f = m.month) AS billing_new_customers
    FROM months m)
  SELECT b.month, b.prepared_on, b.prepared_by, b.adjustment, b.adjustment_note,
         b.active_customers AS board_customers, sys.billing_recognized_payers, sys.telemetry_active_orgs,
         b.mrr_usd AS board_mrr, ROUND(sys.billing_recognized_rev) AS billing_recognized_rev,
         b.revenue_usd AS board_revenue, ROUND(sys.billing_cash_rev) AS billing_cash_rev,
         CASE WHEN ABS(b.revenue_usd - sys.billing_cash_rev) / NULLIF(sys.billing_cash_rev, 0) < 0.01 THEN 'cash'
              WHEN ABS(b.revenue_usd - sys.billing_recognized_rev) / NULLIF(sys.billing_recognized_rev, 0) < 0.01 THEN 'recognized'
              ELSE 'neither' END AS board_revenue_basis,
         b.new_customers AS board_new, sys.billing_new_customers, b.churned_customers AS board_churned
  FROM b JOIN sys USING (month);

-- @out board_vs_systems_monthly
SELECT month, board_customers, billing_recognized_payers, telemetry_active_orgs,
       ROUND(100.0 * board_customers / NULLIF(billing_recognized_payers, 0) - 100, 1) AS board_over_billing_pct,
       board_mrr, billing_recognized_rev, ROUND(100.0 * board_mrr / NULLIF(billing_recognized_rev, 0) - 100, 1) AS board_mrr_over_billing_pct,
       board_revenue, billing_cash_rev, board_revenue_basis, board_new, billing_new_customers, board_churned, adjustment, prepared_by
FROM board_vs_systems ORDER BY month;

-- @out board_revenue_basis_by_period
SELECT board_revenue_basis, COUNT(*) AS months, MIN(month) AS from_month, MAX(month) AS to_month,
       STRING_AGG(DISTINCT prepared_by, ', ') AS prepared_by
FROM board_vs_systems GROUP BY 1 ORDER BY 3;

-- @out board_manual_adjustments
SELECT month, adjustment, adjustment_note, prepared_by, board_customers
FROM board_vs_systems WHERE adjustment IS NOT NULL OR adjustment_note <> '' ORDER BY month;

-- @out board_provenance_summary
SELECT COUNT(*) AS months_reported,
       ROUND(AVG(100.0 * board_customers / NULLIF(billing_recognized_payers, 0) - 100), 1) AS mean_customer_count_gap_pct,
       ROUND(AVG(100.0 * board_mrr / NULLIF(billing_recognized_rev, 0) - 100), 1) AS mean_mrr_gap_pct,
       COUNT(*) FILTER (WHERE adjustment IS NOT NULL) AS months_with_manual_adjustment,
       COUNT(DISTINCT prepared_by) AS preparers,
       COUNT(DISTINCT board_revenue_basis) AS revenue_bases_used,
       ROUND(AVG(date_diff('day', month, prepared_on))) AS mean_days_after_month_start_prepared
FROM board_vs_systems;
