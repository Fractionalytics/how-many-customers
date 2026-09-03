# How many customers?

Two synthetic companies, built to test what a data agent, a semantic-modeling tool, or a person
does when a question has more than one correct answer, and to carry a full customer base audit
and data condition review of the kind a private equity investment committee reads.

Everything is generated. No client data, no real company, no real person. Each `generate.py` is
deterministic: same seed, same bytes, every run.

| | Company 1: Corvane Labs | Company 2: Halyard Systems |
|---|---|---|
| Built for | The customer-count question | The full audit: cohorts, concentration, payback, growth accounting, a board pack to reconcile |
| Files | 5 (CRM, billing customers, invoices, telemetry, spend) | 7 (the same five, plus the board's monthly KPI tab and the acquisition schedules the seller produced on request) |
| History | 47 months of invoices, 14 of telemetry | 47 months of both, plus a legacy book migrated in |
| Lifecycle | Independent draws: no tenure effect, no segment effect | Designed: tenure-dependent churn, tier-linked value and retention, expansion, mix shift, three bought books that retain worse |
| Referee | 758 live on a book of 1,200 | 961 live on a book of 1,454 |
| Folder | `company1/` | `company2/` |

Each company folder holds its generator, its data, `PROFILE.md` (name, backstory, headcount,
acquisitions: the context a diligence memo opens with), `SOLUTIONS.md` (the referee's answers,
which spoil the exercise), and `out/` (the audit's outputs). Company 1 also keeps
`FINDINGS.md`, the audit as it was run against it on 2026-09-02, which is why company 2 exists.

## The audit

`audit/` runs unchanged against either company: the customer base audit and the data condition
review as SQL on DuckDB, with the cross-system reconciliation in Malloy.

```
pip install duckdb pandas
python audit/run.py company2           # every audit/sql/*.sql, outputs to company2/out/

cd audit/malloy && npm install @malloydata/malloy @malloydata/db-duckdb
node audit/malloy/run.js company2      # the reconciliation, one question per file
```

`audit/README.md` has the layout, the conventions, and why there are two engines.

## The question

**How many customers does this company have?** Several answers are available from the data,
all defensible, none obviously wrong: a CRM status, a paid invoice in the last 90 days, any
product usage in the last 30 days, a positive MRR field, the number on the board pack. They do
not agree, and the gap between the highest and the lowest is hundreds of customers on a book of
about a thousand. The fact that would settle it appears in no file, because in a real company
it appears in no file either.

## Vocabulary

- **Defensible count**: any rule's answer. All of them are.
- **Defended count**: the one the audit recommends, with its definition written next to it.
- **The referee**: the generator's simulated state, which scores the rules in `SOLUTIONS.md`
  and appears nowhere else.

## License

MIT. Use it, fork it, change the seed, publish what you find.
