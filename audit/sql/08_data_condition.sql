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
WITH first_use AS (SELECT entity_k AS k, MIN(month) AS first_use FROM usage_month GROUP BY 1),
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
