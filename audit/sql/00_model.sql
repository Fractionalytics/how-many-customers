-- 00_model.sql : the shared model every later file reads.
-- Raw tables, one normalized name key per system, a two-tier entity resolver between CRM and
-- billing, an amortized monthly revenue panel, and a monthly usage panel. Nothing here is a
-- finding; it is the plumbing. The forks inside the plumbing are explored in audit/malloy/.

CREATE OR REPLACE TABLE params AS SELECT DATE '2026-08-20' AS as_of;

CREATE OR REPLACE TABLE crm   AS SELECT * FROM read_csv_auto('crm_accounts.csv',      header=true);
CREATE OR REPLACE TABLE bill  AS SELECT * FROM read_csv_auto('billing_customers.csv', header=true);
CREATE OR REPLACE TABLE inv   AS SELECT * FROM read_csv_auto('billing_invoices.csv',  header=true);
CREATE OR REPLACE TABLE usage AS SELECT * FROM read_csv_auto('product_usage.csv',     header=true);
CREATE OR REPLACE TABLE spend AS SELECT * FROM read_csv_auto('marketing_spend.csv',   header=true);

-- ---------------------------------------------------------------- name keys
-- name_key: fold accents FIRST, then uppercase, then drop everything that is not a letter or
-- digit. Folding before filtering is the whole trick; filtering first deletes the accented
-- letter instead of folding it (SOLUTIONS.md trap 4).
CREATE OR REPLACE MACRO name_key(s) AS
  regexp_replace(upper(strip_accents(s)), '[^A-Z0-9]', '', 'g');

-- canon_key: name_key after the legal-form variants a billing clerk introduces are undone:
-- "Corporation" back to "Corp", "Incorporated" back to "Inc", a trailing "(DBA)" removed.
-- Reversible, mechanical, and it does NOT touch a dropped suffix, which needs tier 2 below.
CREATE OR REPLACE MACRO canon_key(s) AS
  regexp_replace(
    regexp_replace(
      regexp_replace(upper(strip_accents(regexp_replace(s, '\s*\(DBA\)$', ''))),
                     'CORPORATION$', 'CORP'),
      'INCORPORATED$', 'INC'),
    '[^A-Z0-9]', '', 'g');

-- stem_key: the first two words, folded. Two different companies can share a stem
-- (Harborview Supply LLC / Harborview Supply Group), so a stem match is accepted only when
-- it is unambiguous on both sides.
CREATE OR REPLACE MACRO stem_key(s) AS
  name_key(array_to_string(list_slice(string_split(trim(s), ' '), 1, 2), ' '));

-- Billing marks subsidiaries with a suffix (" - EMEA", " - LATAM", " - Subsidiary", " - Div 2").
-- parent_name strips it so a group can be counted as one entity when the business decides that
-- is the right answer. Both forms are kept; the choice is a decision, not a data fix (trap 7).
CREATE OR REPLACE VIEW bill_keyed AS
  SELECT b.*,
         regexp_replace(company_name, ' - (EMEA|LATAM|Subsidiary|Div 2)$', '') AS parent_name,
         company_name <> regexp_replace(company_name, ' - (EMEA|LATAM|Subsidiary|Div 2)$', '') AS is_subsidiary,
         name_key(company_name)  AS k,
         canon_key(regexp_replace(company_name, ' - (EMEA|LATAM|Subsidiary|Div 2)$', '')) AS parent_k,
         stem_key(regexp_replace(company_name, ' - (EMEA|LATAM|Subsidiary|Div 2)$', ''))  AS stem,
         len(string_split(trim(regexp_replace(company_name, ' - (EMEA|LATAM|Subsidiary|Div 2)$', '')), ' ')) AS n_words
  FROM bill b;

CREATE OR REPLACE VIEW crm_keyed AS
  SELECT c.*, name_key(account_name) AS k, canon_key(account_name) AS ck, stem_key(account_name) AS stem
  FROM crm c;

-- ------------------------------------------------------------ entity resolver
-- Tier 1: canonical keys agree exactly. Deterministic.
-- Tier 2: a billing name that dropped its legal suffix (two words) is matched on the stem,
--         but only when that stem points at exactly one unmatched CRM company and exactly one
--         unmatched billing company. Ambiguous stems stay unmatched and are listed in 08.
-- Anything else stays unmatched. The audit reports its coverage before using it.
CREATE OR REPLACE VIEW match_t1 AS
  SELECT c.account_id, b.customer_ref, 1 AS tier
  FROM crm_keyed c JOIN bill_keyed b ON b.parent_k = c.ck;

CREATE OR REPLACE VIEW match_t2 AS
  WITH cu AS (SELECT * FROM crm_keyed  WHERE account_id   NOT IN (SELECT account_id   FROM match_t1)),
       bu AS (SELECT * FROM bill_keyed WHERE customer_ref NOT IN (SELECT customer_ref FROM match_t1)),
       cs AS (SELECT stem, MIN(account_id) AS account_id FROM cu GROUP BY 1 HAVING COUNT(DISTINCT ck) = 1),
       bs AS (SELECT stem, MIN(customer_ref) AS customer_ref FROM bu WHERE n_words = 2 GROUP BY 1 HAVING COUNT(DISTINCT parent_k) = 1)
  SELECT cs.account_id, bs.customer_ref, 2 AS tier FROM cs JOIN bs USING (stem);

CREATE OR REPLACE VIEW bridge_all AS
  SELECT * FROM match_t1 UNION ALL SELECT * FROM match_t2;

-- One CRM account per billing customer: where two CRM rows fold to the same key (the 60
-- re-entered accounts), keep the live one. The stale duplicate is counted in 08, not here.
CREATE OR REPLACE VIEW bridge AS
  SELECT account_id, customer_ref, tier
  FROM (SELECT ba.*, ROW_NUMBER() OVER (PARTITION BY ba.customer_ref
          ORDER BY (c.account_status = 'Active') DESC, c.mrr_usd DESC, ba.account_id) AS rn
        FROM bridge_all ba JOIN crm c USING (account_id))
  WHERE rn = 1;

-- Entity key for a billing customer: the matched CRM canonical key, else its own parent key.
CREATE OR REPLACE VIEW bill_entity AS
  SELECT b.customer_ref, COALESCE(c.ck, b.parent_k) AS entity_k, br.tier
  FROM bill_keyed b
  LEFT JOIN bridge br USING (customer_ref)
  LEFT JOIN crm_keyed c USING (account_id);

-- ------------------------------------------------------------- revenue panel
CREATE OR REPLACE VIEW inv_paid AS
  SELECT i.*, b.contract_type, b.first_invoice_date, b.parent_k, e.entity_k,
         date_trunc('month', i.invoice_date)::DATE AS inv_month
  FROM inv i JOIN bill_keyed b USING (customer_ref) JOIN bill_entity e USING (customer_ref)
  WHERE i.status = 'paid';

-- Cash basis: what arrived, in the month it arrived.
CREATE OR REPLACE VIEW rev_cash AS
  SELECT customer_ref, inv_month AS month, SUM(amount_usd) AS rev
  FROM inv_paid GROUP BY 1, 2;

-- Recognized basis: an annual invoice is spread evenly over the twelve months that start with
-- the invoice month. Monthly and usage invoices land in their own month. Months after the
-- as-of month are deferred revenue and are cut off here.
CREATE OR REPLACE VIEW rev_amort AS
  SELECT customer_ref, month, SUM(rev) AS rev FROM (
    SELECT customer_ref, (inv_month + INTERVAL (k) MONTH)::DATE AS month, amount_usd / 12.0 AS rev
    FROM inv_paid, range(12) t(k) WHERE contract_type = 'annual'
    UNION ALL
    SELECT customer_ref, inv_month, amount_usd FROM inv_paid WHERE contract_type <> 'annual'
  ), params
  WHERE month <= date_trunc('month', as_of)
  GROUP BY 1, 2;

-- Month spine, first invoice month to the as-of month.
CREATE OR REPLACE VIEW months AS
  SELECT (date_trunc('month', (SELECT MIN(invoice_date) FROM inv)) + INTERVAL (m) MONTH)::DATE AS month
  FROM range(0, 12 * 10) t(m)
  WHERE (date_trunc('month', (SELECT MIN(invoice_date) FROM inv)) + INTERVAL (m) MONTH)::DATE
        <= date_trunc('month', (SELECT as_of FROM params));

-- Customer x month panel on the recognized basis, zero-filled from first revenue month to the
-- as-of month. This is the toolkit's "MAU decorated" equivalent, at customer grain.
CREATE OR REPLACE VIEW panel AS
  WITH firsts AS (SELECT customer_ref, MIN(month) AS first_month FROM rev_amort GROUP BY 1)
  SELECT f.customer_ref, f.first_month, m.month,
         COALESCE(r.rev, 0) AS rev,
         COALESCE(LAG(r.rev) OVER (PARTITION BY f.customer_ref ORDER BY m.month), 0) AS rev_prev,
         date_diff('month', f.first_month, m.month) AS months_since_first
  FROM firsts f
  JOIN months m ON m.month >= f.first_month
  LEFT JOIN rev_amort r ON r.customer_ref = f.customer_ref AND r.month = m.month;

-- Same panel on the cash basis, for the comparison in 03.
CREATE OR REPLACE VIEW panel_cash AS
  WITH firsts AS (SELECT customer_ref, MIN(month) AS first_month FROM rev_cash GROUP BY 1)
  SELECT f.customer_ref, f.first_month, m.month,
         COALESCE(r.rev, 0) AS rev,
         COALESCE(LAG(r.rev) OVER (PARTITION BY f.customer_ref ORDER BY m.month), 0) AS rev_prev,
         date_diff('month', f.first_month, m.month) AS months_since_first
  FROM firsts f
  JOIN months m ON m.month >= f.first_month
  LEFT JOIN rev_cash r ON r.customer_ref = f.customer_ref AND r.month = m.month;

-- --------------------------------------------------------------- usage panel
-- Org x month from the telemetry. The org is the unit, so "active user" here means an
-- organization with any activity in the month; the active_users column is kept as a sum.
-- The org slug is the canonical name slugified, so name_key(org_slug) is the entity key.
CREATE OR REPLACE VIEW usage_month AS
  SELECT org_slug, name_key(org_slug) AS entity_k, date_trunc('month', event_date)::DATE AS month,
         COUNT(*) AS active_days, SUM(active_users) AS user_days, SUM(sessions) AS sessions
  FROM usage GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW usage_panel AS
  WITH firsts AS (SELECT org_slug, MIN(month) AS first_month FROM usage_month GROUP BY 1),
       spine AS (SELECT month FROM months WHERE month >= (SELECT MIN(month) FROM usage_month))
  SELECT f.org_slug, f.first_month, s.month,
         COALESCE(u.active_days, 0) AS act,
         COALESCE(LAG(u.active_days) OVER (PARTITION BY f.org_slug ORDER BY s.month), 0) AS act_prev
  FROM firsts f
  JOIN spine s ON s.month >= f.first_month
  LEFT JOIN usage_month u ON u.org_slug = f.org_slug AND u.month = s.month;
