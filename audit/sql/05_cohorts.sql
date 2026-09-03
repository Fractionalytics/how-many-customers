-- 05_cohorts.sql : cohorts by first revenue month, recognized basis.
-- Keyed on MONTHS SINCE FIRST, never calendar year: a calendar-year cohort gives an October
-- signup three months of Y0 and twelve of Y1, and the "retention above 100%" that produces
-- is an artifact that looks exactly like the number everyone wants.

CREATE OR REPLACE VIEW cohort_long AS
  WITH sizes AS (SELECT first_month, COUNT(DISTINCT customer_ref) AS n0, SUM(rev) AS rev0
                 FROM panel WHERE months_since_first = 0 GROUP BY 1)
  SELECT p.first_month AS cohort, p.months_since_first AS k,
         s.n0 AS cohort_size,
         COUNT(*) FILTER (WHERE p.rev > 0) AS active,
         ROUND(100.0 * COUNT(*) FILTER (WHERE p.rev > 0) / s.n0, 1) AS logo_retention_pct,
         ROUND(100.0 * SUM(p.rev) / NULLIF(s.rev0, 0), 1) AS revenue_retention_pct,
         ROUND(SUM(SUM(p.rev)) OVER (PARTITION BY p.first_month ORDER BY p.months_since_first) / s.n0) AS cum_rev_per_cohort_customer
  FROM panel p JOIN sizes s USING (first_month), params
  WHERE p.month < date_trunc('month', as_of)          -- drop the partial as-of month
  GROUP BY p.first_month, p.months_since_first, s.n0, s.rev0;

-- @out cohort_long
SELECT * FROM cohort_long ORDER BY cohort, k;

-- Quarterly cohorts at fixed horizons, built from MONTHLY cohorts, and a horizon is shown for
-- a quarter only when every monthly cohort in that quarter has reached it. Otherwise the
-- quarter's tail horizon is really one monthly cohort, and one large customer swings it.
CREATE OR REPLACE VIEW cohort_monthly AS
  SELECT first_month, months_since_first AS k,
         COUNT(DISTINCT customer_ref) AS n, COUNT(DISTINCT customer_ref) FILTER (WHERE rev > 0) AS active, SUM(rev) AS rev
  FROM panel, params WHERE month < date_trunc('month', as_of) GROUP BY 1, 2;

CREATE OR REPLACE VIEW cohort_quarter_complete AS
  WITH reach AS (SELECT first_month, MAX(k) AS kmax FROM cohort_monthly GROUP BY 1),
       qmin AS (SELECT date_trunc('quarter', first_month)::DATE AS cohort_q, MIN(kmax) AS kmax FROM reach GROUP BY 1)
  SELECT cohort_q, k FROM qmin, range(0, 120) t(k) WHERE k <= kmax;

-- @out cohort_quarterly_logo_retention
WITH q AS (
  SELECT date_trunc('quarter', first_month)::DATE AS cohort_q, k, SUM(active) AS active, SUM(n) AS n
  FROM cohort_monthly GROUP BY 1, 2)
PIVOT (SELECT q.cohort_q, 'm' || lpad(k::VARCHAR, 2, '0') AS m, ROUND(100.0 * active / n, 1) AS ret
       FROM q JOIN cohort_quarter_complete USING (cohort_q, k) WHERE k IN (0,1,3,6,12,18,24,36))
ON m USING FIRST(ret) ORDER BY cohort_q;

-- @out cohort_quarterly_revenue_retention
WITH base AS (SELECT first_month, rev AS rev0 FROM cohort_monthly WHERE k = 0),
q AS (
  SELECT date_trunc('quarter', c.first_month)::DATE AS cohort_q, k, SUM(c.rev) AS rev, SUM(base.rev0) AS rev0
  FROM cohort_monthly c JOIN base USING (first_month) GROUP BY 1, 2)
PIVOT (SELECT q.cohort_q, 'm' || lpad(k::VARCHAR, 2, '0') AS m, ROUND(100.0 * rev / rev0, 1) AS ret
       FROM q JOIN cohort_quarter_complete USING (cohort_q, k) WHERE k IN (0,1,3,6,12,18,24,36))
ON m USING FIRST(ret) ORDER BY cohort_q;

-- @out cohort_quarterly_size_and_cum_revenue
WITH q AS (
  SELECT date_trunc('quarter', cohort)::DATE AS cohort_q, k,
         SUM(cum_rev_per_cohort_customer * cohort_size) / SUM(cohort_size) AS cum_per_cust
  FROM cohort_long GROUP BY 1, 2)
PIVOT (SELECT q.cohort_q, 'm' || lpad(k::VARCHAR, 2, '0') AS m, ROUND(cum_per_cust) AS v
       FROM q JOIN cohort_quarter_complete USING (cohort_q, k) WHERE k IN (0,3,6,12,18,24,36))
ON m USING FIRST(v) ORDER BY cohort_q;

-- Logo retention by contract type at 12 months, by cohort year (thesis leg 1: annual retains better?).
-- @out retention_12m_by_contract_type
WITH p AS (
  SELECT p.*, b.contract_type FROM panel p JOIN bill_keyed b USING (customer_ref))
SELECT EXTRACT(year FROM first_month) AS cohort_year, contract_type,
       COUNT(DISTINCT customer_ref) FILTER (WHERE months_since_first = 0) AS cohort_size,
       ROUND(100.0 * COUNT(DISTINCT customer_ref) FILTER (WHERE months_since_first = 12 AND rev > 0)
             / NULLIF(COUNT(DISTINCT customer_ref) FILTER (WHERE months_since_first = 12), 0), 1) AS logo_retention_12m_pct,
       ROUND(100.0 * COUNT(DISTINCT customer_ref) FILTER (WHERE months_since_first = 24 AND rev > 0)
             / NULLIF(COUNT(DISTINCT customer_ref) FILTER (WHERE months_since_first = 24), 0), 1) AS logo_retention_24m_pct
FROM p, params WHERE month < date_trunc('month', as_of)
GROUP BY 1, 2 ORDER BY 1, 2;

-- The cash-basis cohort, for the record: on cash, an annual customer is "inactive" for
-- eleven months of every twelve, so the logo curve falls off a cliff at month 1.
-- @out cash_basis_cohort_cliff
SELECT months_since_first AS k,
       ROUND(100.0 * COUNT(*) FILTER (WHERE rev > 0) / COUNT(*), 1) AS logo_retention_cash_pct
FROM panel_cash, params WHERE month < date_trunc('month', as_of) AND months_since_first IN (0,1,2,3,6,11,12,13,24)
GROUP BY 1 ORDER BY 1;
