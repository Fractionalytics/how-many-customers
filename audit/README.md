# The customer base audit and the data condition review

Two deliverables, rebuilt from the five files in this repository, in the form a private equity
investment committee would read them:

- **A customer base audit.** Cohorts, concentration and payback rebuilt from the transaction
  records and the event log, with the segments carrying the thesis named. Concentration first,
  because revenue resting on a few customers is a risk the multiple should price. Growth
  accounting, quick ratio and net revenue retention follow the TheVentureCity
  [Data Pipeline Toolkit](https://github.com/theventurecity/data-toolkit) definitions, in SQL.
- **A data condition review.** Which reported numbers come from a system, and which get rebuilt
  by hand every month. Manual processes pass diligence intact and then set the ceiling on the
  operating plan, because every initiative built on those numbers inherits the manual step.

Everything is rerunnable. The numbers in `FINDINGS.md` and in the deck come from these files
and nowhere else.

## Layout

```
audit/
  run.py            runs every audit/sql/*.sql in order on an in-memory DuckDB, against one company folder
  sql/
    00_model.sql    raw tables, name keys, the two-tier entity resolver, the revenue and usage panels
    01_customer_count.sql
    02_concentration.sql
    03_revenue_growth_accounting.sql   new / retained / expansion / contraction / resurrected / churned, quick ratio, NRR, GRR
    04_user_growth_accounting.sql      the same on active organizations from the telemetry
    05_cohorts.sql
    06_clv_payback.sql
    07_segments.sql
    08_data_condition.sql
  malloy/
    model.malloy    the semantic layer: one source per system, "customer" defined once as named measures
    NN_*.malloy     the reconciliation, one question per file
    run.js          runs them
```

Outputs land in `<company>/out/`, one CSV per labelled query, and each company's
`FINDINGS.md` reads them.

## Run it

The first argument is the company folder (`company1` or `company2`).

```
pip install duckdb pandas
python audit/run.py company2            # everything, outputs to company2/out/
python audit/run.py company2 03         # one file (00_model.sql is always loaded first)
```

Each `SELECT` marked with a `-- @out <label>` comment is printed and written to
`<company>/out/<file>__<label>.csv`. Two optional files, `board_kpis.csv` and
`acquisition_schedules.csv`, are loaded when the company has them and created empty when it
does not, so every query runs against both companies.

The Malloy side needs Node and the Malloy DuckDB driver:

```
cd audit/malloy
npm install @malloydata/malloy @malloydata/db-duckdb
node run.js company2                            # every query, in order
node run.js company2 05_join_folded.malloy --sql   # one query, plus the SQL Malloy generated
```

`run.js` prepends `model.malloy` to each query file, so the model is written once and every
query reads the same definitions.

## Why two engines

SQL is what the room can rerun, and the toolkit's arithmetic (a customer-by-month panel, then
classification against the previous month) is plain window-function SQL. Malloy is where the
definition of "customer" is written once, as a named measure, and pointed at four systems that
never agreed on it. When the business changes the definition, one line changes. The forks the
reconciliation has to surface (accent folding that recovers 79 companies and fans the join out,
near-collisions a fuzzy matcher would merge, subsidiaries that may or may not be one customer)
are each one query in `malloy/`.

## Conventions

- The as-of date is 2026-08-20 and every window is inclusive. Both are choices; both are stated.
- Revenue is on a **recognized** basis unless a table says cash: an annual invoice is spread over
  the twelve months starting with the invoice month, and anything past the as-of month is
  deferred, not revenue. The cash-basis versions are kept so the difference can be shown.
- Cohorts are keyed on months since first revenue, never on calendar year.
- The entity resolver is two tiers: exact canonical key, then an unambiguous stem match for
  billing names that dropped their legal suffix. Its coverage is reported before any segment
  table uses it, and the stems it refused are listed.
- No conclusions live in SQL. The queries print numbers; `FINDINGS.md` reads them.
