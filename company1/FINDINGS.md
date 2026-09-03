# Findings, stage 1: the numbers

As of 2026-08-20, seed 20260820. Every figure below is printed by `python audit/run.py` or
`node audit/malloy/run.js` and sits in `audit/out/` as a CSV. Nothing here is projected; nothing
is typed in by hand. Conclusions are deliberately thin at this stage: this is the sheet the
story gets shaped from, not the story.

Conventions: windows are inclusive; revenue is recognized (annual invoices spread over twelve
months) unless a table says cash; cohorts are keyed on months since first revenue; the as-of
month (August 2026) is partial and is excluded from every trend.

---

## 1. How many customers?

Eleven defensible rules, three systems, one question.

| # | Rule | Customers |
|---|---|---|
| 1 | CRM `account_status = Active`, rows | 756 |
| 2 | CRM Active, distinct entities (folded name key) | 751 |
| 3 | CRM `mrr_usd > 0` and not Churned, rows | 739 |
| 4 | CRM `mrr_usd > 0` and not Churned, entities | 719 |
| 5 | Billing: paid invoice in the last 90 days, `customer_ref` | 485 |
| 6 | Billing: paid invoice in the last 90 days, parent entity | 476 |
| 7 | Billing: paid invoice in the last 365 days | 890 |
| 8 | Billing: contract-aware (monthly and usage 90 days, annual 365 days) | 778 |
| 9 | Billing: recognized revenue above zero in the as-of month | 612 |
| 10 | Product: any usage in the last 30 days | 770 |
| 11 | Product: monthly active organizations, last complete month (July) | 781 |

Spread between the four rules a company actually uses (1, 3, 5, 10): **485 to 770, a gap of
285, 59 percent of the lowest.** Ground truth, which appears in no file, is 758.

Why rule 5 is the trap: 534 of 1,144 billing customers are on annual contracts, and 397 of
those last paid more than 90 days ago. 293 of them paid between 91 and 365 days ago, which is
what a current annual customer looks like in August. The rule is correct, the data is correct,
and the answer is wrong by more than a third of the base.

The same fork one level down: an inclusive boundary gives 485 and 770; an exclusive boundary
gives 484 and 767. Nobody writes that down either.

The status picklist: Active 756, Churned 246, Inactive 117, blank 90. The blank rows carry an
average MRR of $2,012 against $2,024 for Active, so they are not dead records; they are records
nobody touched.

## 2. Concentration

Trailing twelve months of paid cash, billing grain.

| | |
|---|---|
| Paying customers in the window | 889 (866 parent entities) |
| TTM paid | $19,634,907 |
| Mean per customer | $22,087 |
| Median per customer | $6,668 |
| Largest customer | $132,109 |

| Top N customers | Share, by `customer_ref` | Share, by parent entity |
|---|---|---|
| 1 | 0.7% | 0.8% |
| 5 | 3.2% | 3.5% |
| 10 | 6.3% | 6.6% |
| 20 | 12.3% | 12.5% |
| 50 | 28.3% | 28.6% |
| 100 | 48.6% | 49.1% |

Lorenz points: the top 10 percent of customers carry 44.9 percent of revenue, the top 20
percent carry 70.0 percent, the top 50 percent carry 92.6 percent. Herfindahl-Hirschman index
33, which implies an effective customer count of 303.

The CRM's answer to the same question (annualized `mrr_usd` on non-churned accounts): top 10 =
5.4 percent, top 50 = 25.0 percent, against billing's 6.3 and 28.3. The two systems also
disagree on who the top ten are: only four names appear on both lists. The revenue base itself
has four values:

| Basis | USD | Customers |
|---|---|---|
| Billing, paid cash, TTM | $19,634,907 | 889 |
| Billing, recognized, TTM | $19,612,578 | 969 |
| CRM, Active x `mrr_usd` x 12 | $18,365,859 | 756 |
| CRM, not Churned and `mrr_usd` > 0, x 12 | $22,806,832 | 739 |

By contract type: annual customers are 49.4 percent of TTM revenue and 46 of the top decile;
monthly 40.7 percent and 34; usage 9.9 percent and 9.

**Reading:** this book is unconcentrated. No customer reaches 1 percent. Against the concern
the service description leads with, the finding is a clean bill. Whether that is realistic is
taken up in section 9.

## 3. Revenue growth accounting

Toolkit definitions, recognized basis, per customer per month. Last twelve complete months
(August 2025 to July 2026):

| Basis | Mean quick ratio | Min | Max | Churned, % of revenue | Resurrected, % of revenue |
|---|---|---|---|---|---|
| Recognized | 1.16 | 0.29 | 2.26 | 7.4% | 4.9% |
| Cash | 1.00 | 0.43 | 1.39 | 57.7% | 42.1% |

Same invoices. On the cash basis, more than half of each month's revenue "churns" and 42
percent "resurrects", because an annual customer pays once and is silent for eleven months.
The cash-basis growth accounting describes the invoice calendar, not the customers.

Monthly recognized revenue rose from $1.39M in January 2025 to $1.77M in December 2025 and has
drifted down to $1.56M by July 2026 (`rev_ga_recognized_monthly`). Paying customers on the
recognized basis peaked at 797 in December 2025 and stood at 734 in July 2026.

Twelve-month retention, base month to the same month a year later, recognized basis:

| Base months | Mean NRR | Mean GRR | Mean logo retention |
|---|---|---|---|
| Aug 2024 to Jul 2025 | 80.7% | 76.3% | 79.4% |

The trend inside that is the finding: NRR was 92 to 95 percent for base months in 2023, 85 to
88 percent through 2024, and 70 to 78 percent for base months in mid-2025. Logo retention over
the same span fell from 94 percent to 71 percent. On the cash basis, the July 2025 base month
reads 59.7 percent NRR against 71.1 recognized.

## 4. Active-organization growth accounting

From the telemetry, organization as the unit.

| Month | Active orgs | New | Retained | Resurrected | Churned | Quick ratio |
|---|---|---|---|---|---|---|
| 2025-08 | 1,047 | 102 | 945 | 0 | -15 | 6.80 |
| 2025-11 | 994 | 0 | 974 | 20 | -32 | 0.63 |
| 2026-02 | 956 | 0 | 935 | 21 | -43 | 0.49 |
| 2026-05 | 883 | 0 | 862 | 21 | -61 | 0.34 |
| 2026-07 | 781 | 0 | 781 | 0 | -34 | 0.00 |

Monthly active organizations fell from 1,047 to 781 in eleven months, and **the telemetry
records zero new organizations after September 2025**, while billing added between 38 and 101
new customers every quarter over the same period. The product log does not observe onboarding.
Related: 244 of the 970 organizations that match to billing show usage more than 30 days before
their first invoice, by 207 days on average.

History depth: the telemetry holds 14 months (2025-07-17 to 2026-08-20); invoices, CRM and
spend hold 47.

Paying versus using in July 2026, through the entity resolver: 643 organizations pay and use,
79 pay and do not use, 138 use and do not pay.

## 5. Cohorts

Quarterly cohorts by first revenue month, logo retention at months since first (recognized
basis):

| Cohort | m1 | m3 | m6 | m12 | m18 | m24 | m36 |
|---|---|---|---|---|---|---|---|
| 2022 Q4 | 94.1 | 97.1 | 97.1 | 94.1 | 94.1 | 85.3 | 76.5 |
| 2023 Q2 | 93.2 | 91.8 | 95.9 | 93.2 | 90.4 | 78.1 | 53.4 |
| 2023 Q4 | 93.9 | 95.5 | 95.5 | 89.4 | 93.9 | 81.8 | |
| 2024 Q2 | 95.3 | 96.9 | 93.8 | 90.6 | 85.9 | 68.8 | |
| 2024 Q4 | 92.0 | 94.3 | 90.8 | 75.9 | 71.3 | | |
| 2025 Q2 | 95.1 | 90.1 | 97.5 | 79.0 | | | |
| 2025 Q3 | 88.6 | 91.4 | 84.3 | 65.4 | | | |

Twelve-month logo retention by cohort year and contract type: 2023 cohorts 94.1 percent annual
and 92.9 monthly; 2024 cohorts 86.1 and 82.3; 2025 cohorts 67.6 and 84.3. Later cohorts retain
worse on every horizon that can be measured, and the 2025 annual cohort is the worst cell in
the table.

Cumulative recognized revenue per cohort customer: $8,200 at month 3, $14,300 at month 6,
$26,300 at month 12, $51,600 at month 24, $72,400 at month 36 (weighted across every cohort
old enough).

The cash-basis cohort, for the record: logo retention reads 48.6 percent at month 1, 49.1 at
month 11, 84.2 at month 12, 46.6 at month 13. That is the annual invoice calendar, not the
customers, and it is what any cohort chart built on payments rather than recognized revenue
shows for a book that is 46 percent annual.

## 6. Lifetime value, acquisition cost, payback

Observed lifetime paid revenue per billing customer: mean $50,361, median $14,212, ratio 3.54.
By contract: annual mean $59,958, monthly $41,056, usage $48,601. A mean-based CLV on this
book overstates the typical customer by three and a half times.

Cohort CAC, spend lagged one month over new customers in the quarter, two denominators:

| Quarter | Spend | New billing customers | New CRM accounts | CAC per billing customer | CAC per CRM account | Gap |
|---|---|---|---|---|---|---|
| 2024 Q3 | $402,731 | 101 | 98 | $3,987 | $4,109 | +3.1% |
| 2025 Q1 | $441,856 | 67 | 67 | $6,595 | $6,595 | 0.0% |
| 2025 Q4 | $546,766 | 67 | 81 | $8,161 | $6,750 | -17.3% |
| 2026 Q1 | $504,385 | 47 | 79 | $10,732 | $6,385 | -40.5% |
| 2026 Q2 | $574,169 | 38 | 69 | $15,110 | $8,321 | -44.9% |

Spend rose 43 percent from 2024 Q3 to 2026 Q2 while new billing customers fell from 101 to 38
a quarter, so CAC on the billing denominator nearly quadrupled. The CRM denominator hides most
of that, because CRM accounts get created whether or not they ever pay: the gap between the
two answers is 45 percent in the latest full quarter.

Cumulative spend over every count rule (the denominator isolated; not a defensible CAC on its
own, and the error is the lesson): $5,699 per CRM account ever, $9,114 per CRM Active, $8,949
per usage-30d organization, $14,207 per paid-in-90-days customer. Highest is 2.5 times lowest.

Payback by cohort quarter: 1 to 3 months for every cohort through 2025 Q3, 5 months for 2026
Q1. On contract type, blended CAC of $5,610 against a first-month cash receipt of $26,034 for
annual customers and $2,020 for monthly: payback 0.2 months on cash for annual, 2.8 for
monthly, 2.6 to 2.7 on recognized revenue for both.

CAC by channel is not computable, four ways: 0 of 282 spend rows carry any account key;
finance books 6 channels and sales typed 23 distinct `lead_source` values; `lead_source` is
blank on 100 percent of the 520 accounts created before 2024-06-01 (the field did not exist)
and 12 percent of the 689 after; and the acquired book (160 companies, per the answer key) is
undetectable: no month of account creation exceeds 1.44 times the median, because the three
books were signed over 120-day windows rather than on one day.

## 7. Segments

Entity resolver coverage, stated before use: 935 of 1,144 billing customers match a CRM
account on the exact canonical key and 120 more on an unambiguous stem, 92.2 percent of
customers and 93.7 percent of TTM revenue. 89 remain unmatched; the stems refused as ambiguous
are dominated by the accented families (Sao Bento, Garcia Sistemas, Hernandez Retail, Perez
Group, Ferreira Servicos), each of which has six to eight distinct CRM companies behind a
two-word billing name.

Twelve-month retention, base months in the last 24 months:

| Segment | Customers in base | Logo retention | NRR | GRR |
|---|---|---|---|---|
| Contract: annual | 370 | 82.9% | 83.3% | 79.9% |
| Contract: monthly | 373 | 74.5% | 77.1% | 71.8% |
| Contract: usage | 81 | 77.9% | 77.6% | 71.9% |
| Tier: Enterprise | 183 | 81.0% | 84.9% | 80.2% |
| Tier: Growth | 386 | 77.4% | 78.5% | 74.2% |
| Tier: Starter | 190 | 79.3% | 81.1% | 76.4% |
| Sector, best: Energy | 78 | 85.9% | 87.2% | 82.1% |
| Sector, worst: Construction | 75 | 71.6% | 69.0% | 64.4% |
| Owner, best: s.okoro | 122 | 82.0% | 84.7% | 80.4% |
| Owner, worst: p.lindqvist | 138 | 76.6% | 78.0% | 73.1% |

Revenue share: annual 49.4 percent, monthly 40.7, usage 9.9. Sectors run from Fintech at 11.7
percent to Hospitality at 6.9; no sector dominates. Owners run from 17.3 to 14.0 percent.

`plan_tier` does not predict the money: mean MRR is $2,689 for Enterprise, $2,541 for Starter,
$2,471 for Growth, and the 90th percentile is $7,800 to $8,400 in all three. The field is
decoration.

Thesis test, as the numbers stand: leg 1 (annual contracts retain and expand better) reads
plausible on the current seed, 82.9 against 74.5 logo and 83.3 against 77.1 NRR. Leg 2 (the
acquired books retain as well as organic) cannot be tested, because nothing in any file
identifies an acquired customer. Section 9 says why leg 1 should not be trusted either.

## 8. Data condition

| File | Primary key | Rows | Distinct entities (name key) | Shared key |
|---|---|---|---|---|
| crm_accounts | account_id | 1,209 | 1,157 | none |
| billing_customers | customer_ref | 1,144 | 1,110 | none |
| billing_invoices | invoice_id | 13,780 | 1,042 customers | customer_ref, to billing only |
| product_usage | (org_slug, event_date) | 171,728 | 1,072 | none |
| marketing_spend | (month, channel) | 282 | 6 channels | none: no account key at all |

- `email_domain` looks like a key and is not: 59 distinct domains across 1,209 rows;
  `whitmore.com` covers 38 unrelated companies.
- The primary-key duplicate check returns 0. The entity check returns 52 CRM name keys with
  two rows each, and 34 billing parent keys billed as two customers.
- After both resolver tiers: 89 billing customers have no CRM account, 130 CRM accounts have
  no billing customer, 102 billing customers were never invoiced, 102 usage organizations
  match no billing customer, 42 match no CRM account, and 0 invoices point at an unknown
  customer.
- Invoice status mix: paid 93.8 percent of gross, refunded 2.9, void 2.5, failed 0.9. Which of
  those count is a decision.
- Fields with a history: `account_status` and `mrr_usd` are overwritten in place, 0 months
  reconstructible. `lead_source` exists for 26 months. Invoices and spend hold 47 months; the
  telemetry holds 14.
- KPI provenance (`kpi_provenance`): of ten numbers a board would see, the customer count has
  eleven defensible values here and no system of record; MRR, TTM revenue and blended CAC each
  have four to seven; CAC by channel has none; concentration and NRR have two, one per system
  or basis.

**What is missing from the fixture for this half of the review:** the spreadsheet. The site's
definition is which numbers come from a system and which get rebuilt by hand each month, and
that needs an object to compare against. `board_kpis.csv` is agreed and not yet built; see
section 9.

---

## 9. What the fixture can carry, and what it cannot

The fixture was built to make the count question hard, and it does that well: every one of the
sixteen traps reproduces through SQL and through Malloy, and the eleven-rule table above is
the strongest exhibit in the set. The audit layers on top of it were built for a different
purpose, and the run exposes where the ground-truth pass underneath them is too simple. These
are measurements, not opinions, and each one would be caught by a reader who reruns the files.

1. **Churn does not exist before September 2024.** `churned_on` is drawn uniformly from the
   last 700 days, so every twelve-month window that closes before then shows 92 to 95 percent
   NRR and every window after shows 70 to 80. The "deteriorating retention" story in sections
   3 and 5 is real in the data and is an artifact of the draw.
2. **The telemetry ignores the signing date.** Every organization has usage for the same 400
   days regardless of when it became a customer: zero new organizations for eleven months
   while billing adds 40 to 100 a quarter, and 244 organizations using the product seven
   months before their first invoice.
3. **Every segment is an independent draw.** Contract type, tier, sector, owner and the churn
   decision do not touch each other in the generator, so the annual-versus-monthly gap in
   section 7 and the Construction-versus-Energy gap are seed noise. A canonical audit that
   "finds" seed noise is worse than none: a reader who changes the seed gets a different story.
4. **MRR is capped near $10,000, so the book is flatter than any real one.** Top ten at 6.3
   percent, HHI 33. Concentration is the first slide, and on this book it is empty.
5. **Spend is small against revenue, so payback is two months.** Real B2B books pay back in 12
   to 24; an investment committee would stop reading at a 2-month payback.
6. **The board spreadsheet does not exist yet** (agreed, not built).

None of this touches the sixteen traps, which live in the systems layer (keys, spellings,
statuses, subsidiaries, invoice states, the lead-source vocabulary) and survive any change to
the lifecycle underneath them.

### Proposal: a second ground-truth pass in generate.py

Keep every system-layer trap byte for byte in spirit; replace the lifecycle draw with one that
has designed structure, then regenerate the five files plus two new ones:

- **Value distribution** with a real tail: log-normal MRR, a handful of $25,000 to $60,000 a
  month accounts, so the top ten land near 20 to 25 percent and the largest customer near 5.
- **Tenure-dependent churn hazard**, higher in months 1 to 6 and lower after, running from the
  first month of the history, so cohort curves decay the way real ones do and NRR has a level
  rather than a cliff.
- **Designed segment effects**: annual contracts with a lower hazard and real expansion (seat
  growth in `mrr` over time, so NRR carries genuine expansion revenue); one weak sector; one
  strong owner; and the three acquired books with a materially worse hazard, so thesis leg 2
  fails on the evidence and the audit gets to say so.
- **Cohort quality drift** in one direction, so there is a trend that is a finding rather than
  an artifact.
- **Spend recalibrated** so blended payback lands in the 12 to 20 month range and rises in the
  most recent cohorts.
- **Telemetry gated on the signing date and the churn date**, with usage intensity that decays
  before churn (a leading indicator the audit can show), and a telemetry retention window that
  is a parameter (full history, or a realistic 24 months).
- **`board_kpis.csv`**: the CFO's monthly tab. A customer count and MRR lifted from the CRM on
  whatever day the deck was built, a hand-typed adjustment column that appears some months
  with a note and no reproducibility, a revenue line that switches from cash to recognized
  when a new controller arrives, and `prepared_on` / `prepared_by` columns. No system can
  reproduce its series, and that is the data condition review's object.

Cost: `SOLUTIONS.md` and the README's headline numbers (756 / 770 / 475 / 758) change and get
re-verified; the lab answer key in the strategy repo goes stale and is kept as history. The
audit code in this directory does not change; it reruns on the new files as it stands.

**Recommendation: do it.** Section 9 is the case; sections 1 and 8 show the parts that already
work and would carry over untouched.
