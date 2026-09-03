# Findings, stage 1, second edition: Halyard Systems by the numbers

As of 2026-08-20, seed 20260903. Every figure is printed by `python audit/run.py company2` or
`node audit/malloy/run.js company2` and sits in `company2/out/` as a CSV. Nothing is projected
and nothing is typed in. This is the sheet the story gets shaped from; the story is the deck.

Vocabulary: a **defensible count** is any rule's answer; the **defended count** is the one the
audit recommends with its definition written next to it; the **referee** is the generator's
simulated state, used only in `SOLUTIONS.md`. Conventions: windows inclusive; revenue on the
recognized basis (an annual invoice spread over the twelve months from its invoice month)
unless a table says cash; cohorts keyed on months since first revenue; August 2026 is partial
and is excluded from every trend. Tables are monthly in `out/`; some are shown quarterly here
for width.

Benchmarks, where one applies, are from Lenny's Newsletter "What is good retention": SMB and
mid-market SaaS, six-month logo retention 60 percent good and 80 great, twelve-month NRR 90 good
and 110 great; enterprise SaaS, 70 and 90, 110 and 130.

Company context is in `PROFILE.md`: Denver, founded 2016, about 212 employees, Bramblewood
Capital platform since November 2023, three add-ons, Stripe since October 2022, a controller who
assembles the board pack by hand.

---

## 1. How many customers?

| # | Rule | Customers |
|---|---|---|
| 1 | CRM `account_status = Active`, rows | 892 |
| 2 | CRM Active, distinct entities | 884 |
| 3 | CRM `mrr_usd > 0` and not Churned, rows | 1,110 |
| 4 | CRM `mrr_usd > 0` and not Churned, entities | 1,076 |
| 5 | Billing: paid invoice in the last 90 days, `customer_ref` | 691 |
| 6 | Billing: paid invoice in the last 90 days, parent entity | 674 |
| 7 | Billing: paid invoice in the last 365 days | 1,066 |
| 8 | Billing: contract-aware (monthly and usage paid in 90 days, annual in 365) | 954 |
| 9 | Billing: recognized revenue above zero in August | 728 |
| 10 | Product: any usage in the last 30 days | 938 |
| 11 | Product: monthly active organizations, July | 937 |
| 12 | Board pack, July 2026 | 1,050 |

Spread across the four a company actually uses (1, 3, 5, 10): **691 to 1,110**, 419 customers,
61 percent of the lowest. The board's own number is above all of them but one.

**Defended count: 954**, the contract-aware billing rule, stated as "a billing customer who has
paid within one cadence of its contract." Why the others miss: rule 5 excludes 356 of the 411
annual customers because they last paid more than 90 days ago (263 of them between 91 and 365
days ago, which is a current annual customer in August); rule 1 misses live accounts sitting in
the 112 blank and 134 Inactive rows (average MRR $2,210 and $2,220, so not dead); rule 3 counts
215 Churned rows and most Inactive and blank rows whose `mrr_usd` was never zeroed; rule 10
counts churned organizations still logging in and misses dormant ones.

Boundary check: 691 and 938 inclusive, 690 and 937 exclusive.

## 2. Concentration

TTM paid cash, billing grain. The base here is everyone who paid in the trailing twelve months,
which includes customers who churned mid-year; it is the right base for pricing TTM revenue and
it is a different question from section 1.

| | |
|---|---|
| Paying customers, TTM | 1,065 (1,033 parent entities) |
| TTM paid | $39,592,455 |
| Mean / median per customer | $37,176 / $9,830 |
| Largest customer | $1,524,796 (3.9 percent) |

| Top N | Share by `customer_ref` | Share by parent entity |
|---|---|---|
| 1 | 3.9% | 3.9% |
| 5 | 12.9% | 12.9% |
| 10 | 19.4% | 19.4% |
| 20 | 27.5% | 27.5% |
| 50 | 43.7% | 43.9% |
| 100 | 59.0% | 59.5% |

Lorenz: the top 10 percent of customers carry 60.5 percent of revenue, the top 20 percent carry
75.9 percent, the top 50 percent carry 93.7. HHI 70, effective customer count 142. This is a
normal mid-market book: close to 80/20, no single customer above 4 percent.

The ten largest, and how they are held:

| Customer | Contract | TTM | Share |
|---|---|---|---|
| Meridian Cascade | usage | $1,524,796 | 3.9% |
| Verdigris Pioneer Holdings | **monthly** | $1,344,654 | 3.4% |
| Acme Onyx | **monthly** | $768,500 | 1.9% |
| Oakfield Compass Labs | usage | $754,599 | 1.9% |
| Pemberton Clinical LLC | annual | $733,679 | 1.9% |
| Pinnacle Digital Group | usage | $672,295 | 1.7% |
| Dovetail Trading Labs | annual | $644,826 | 1.6% |
| Larkspur Freight Holdings | annual | $444,373 | 1.1% |
| Yellowfin Clinical | annual | $403,949 | 1.0% |
| Meridian Atlas Group | annual | $399,942 | 1.0% |

Five of the ten are not on annual contracts. Annual customers are 57.7 percent of TTM revenue
and 84 of the 106 customers in the top decile.

The CRM disagrees on the list: its top ten, by annualized `mrr_usd`, starts with Oakfield Compass
Labs and Meridian Cascade tied at $1,620,000 and includes Harborview Quantum Holdings, which
billing does not have in its top ten. Top-ten share by system: billing 19.4 percent, CRM 20.4.
The revenue base has four values: $39.6M cash, $37.3M recognized, $39.8M CRM Active annualized,
$46.3M CRM not-Churned annualized.

## 3. Revenue growth accounting

Last twelve complete months, August 2025 to July 2026:

| Basis | Mean quick ratio | Min | Max | Churned, % of revenue | Resurrected, % of revenue |
|---|---|---|---|---|---|
| Recognized | 1.97 | 0.78 | 4.04 | 2.5% | 1.3% |
| Cash | 1.16 | 0.42 | 2.18 | 59.8% | 46.6% |

Same invoices. On cash, six tenths of each month's revenue "churns" and half "resurrects",
because an annual customer pays once a year. Recognized monthly revenue rose from $2.22M in
January 2025 to $3.48M in July 2026 (`rev_ga_recognized_monthly`); paying customers on the
recognized basis from 611 to 899.

Twelve-month retention, base month to the same month a year later:

| Base months | Mean NRR | Mean GRR | Mean logo retention |
|---|---|---|---|
| Aug 2024 to Jul 2025 | 96.5% | 83.7% | 79.1% |

Against the benchmark, 96.5 percent NRR is "good" for mid-market (90) and short of "great"
(110). On the cash basis the same series swings from 58 to 111 percent month to month.

## 4. Active-organization growth accounting

From the telemetry, organization as the unit, full history (48 months against 47 of invoices).
Monthly active organizations rose from 89 in October 2022 to 869 in November 2025 and 937 in
July 2026, with 14 to 48 new organizations a month and 4 to 22 churned; the organization quick
ratio ran between 1.1 and 7.7 over the last two years and month-over-month retention between
97 and 99 percent (`user_ga_monthly`). New organizations in the telemetry now track new billing
customers, which they did not in company 1.

Paying versus using, July 2026, through the entity resolver: 796 organizations pay and use, 75
pay and do not use, 141 use and do not pay. The 75 include the 49 dormant subscriptions the
referee knows about plus resolver misses; the 141 include churned organizations still logging in
and organizations billing cannot match.

## 5. Cohorts

Quarterly cohorts by first revenue month, logo retention at months since first, shown only where
every monthly cohort in the quarter has reached the horizon:

| Cohort | m1 | m3 | m6 | m12 | m18 | m24 | m36 |
|---|---|---|---|---|---|---|---|
| 2022 Q4 (includes the legacy migration) | 97.3 | 93.5 | 91.9 | 80.0 | 75.7 | 71.9 | 66.5 |
| 2023 Q1 | 92.9 | 85.7 | 80.4 | 67.9 | 64.3 | 58.9 | 55.4 |
| 2023 Q3 | 96.1 | 86.3 | 80.4 | 68.6 | 64.7 | 51.0 | |
| 2024 Q1 | 93.5 | 88.0 | 85.9 | 67.4 | 58.7 | 58.7 | |
| 2024 Q3 | 93.2 | 94.9 | 83.1 | 66.1 | 64.4 | | |
| 2025 Q1 | 95.1 | 95.1 | 85.4 | 73.8 | | | |
| 2025 Q3 | 95.6 | 88.5 | 83.2 | 62.9 | | | |
| 2026 Q1 | 94.1 | 86.1 | | | | | |

Six-month logo retention runs 80 to 87 percent, which is "great" on the SMB and mid-market
benchmark (80). Twelve-month sits at 63 to 74 for organic cohorts. The 2022 Q4 cohort is 185
customers against a 51 to 62 run rate and retains best at every horizon, because 140 of them
are the legacy book re-invoiced when Stripe went live: survivors, not a cohort.

Twelve-month logo retention by cohort year and contract type: annual 78.5 / 74.3 / 75.5 / 79.3
for 2022 to 2025 cohorts; monthly 77.5 / 64.5 / 65.4 / 64.2. Inside a contract type the number
is flat from 2023 on. The blended cohort number drifts because the mix does (section 7).

Cumulative recognized revenue per cohort customer, all cohorts old enough: $10,600 at month 3,
$18,400 at month 6, $33,200 at month 12, $68,200 at month 24, $113,100 at month 36.

The cash-basis cohort, for the record: logo retention reads 65.7 at month 1, 48.4 at month 11,
70.7 at month 12, 47.0 at month 13. That is the invoice calendar on a book that is 29 percent
annual by logo and 58 percent by revenue.

## 6. Lifetime value, acquisition cost, payback

Observed lifetime paid revenue per billing customer: mean $70,963, median $15,600, ratio 4.55.
Annual $138,795 mean against monthly $32,623.

Cohort CAC, spend lagged one month over new customers, two denominators (quarters):

| Quarter | Spend | New billing | New CRM | CAC per billing customer | CAC per CRM account |
|---|---|---|---|---|---|
| 2022 Q4 | $1,044,315 | 118 | 41 | $8,850 | $25,471 |
| 2023 Q3 | $1,540,891 | 51 | 69 | $30,214 | $22,332 |
| 2024 Q2 | $1,793,077 | 119 | 72 | $15,068 | $24,904 |
| 2025 Q1 | $1,952,154 | 103 | 94 | $18,953 | $20,768 |
| 2025 Q4 | $2,486,442 | 91 | 88 | $27,324 | $28,255 |
| 2026 Q2 | $2,544,281 | 93 | 90 | $27,358 | $28,270 |

Spend rose 2.4x over the history. The 2022 Q4 figure is the migration cohort and not a CAC.
The two denominators disagree by up to 65 percent in a quarter (2024 Q2, when Northgate's
accounts were re-papered in billing). Cumulative spend of $30.78M over every count rule: $21,025
per CRM account ever, $34,507 per CRM Active, $44,545 per paid-in-90-days customer.

Payback, cohort CAC against cumulative recognized revenue per cohort customer: 8 to 14 months for
organic cohorts from 2023 Q1 through 2025 Q2 (2 months for the migration cohort). By contract, on
a blended CAC of $22,612: annual customers 5.0 months on recognized revenue and 0.4 on cash
(they pay twelve months up front, $53,314 on average in month one); monthly customers 13.8 on
recognized and 14.3 on cash. The referee's own honest blended figure is $26,673 per organic
customer, 9.8 months on revenue and 12.2 at an 80 percent gross margin.

CAC by channel is not computable, four ways: 0 of 282 spend rows carry an account key; finance
books 6 channels and sales typed 23 `lead_source` values; `lead_source` is blank on 97.8 percent
of the 744 accounts created before the field existed (2024-06-01) and 10.3 percent after; and
the acquired book carries no channel of its own. The creation-date spike test that found nothing
on company 1 is now fooled the other way: CRM created dates run back to 2016, so the median month
holds 7 accounts and every billing-era month reads as a spike. Restrict it to the billing era.

## 7. Segments, and the thesis

Resolver coverage first: 1,125 of 1,399 billing customers match a CRM account on the exact
canonical key and 154 more on an unambiguous stem, 91.4 percent of customers and 88.5 percent
of TTM revenue. The unmatched residue carries $4.57M of TTM revenue and is dominated by the
accented families (Andre Freres, Perez Group, Hernandez Retail, Guimaraes Log, Sao Bento, each
with eight to ten distinct CRM companies behind a two-word billing name).

Twelve-month retention, base months in the last 24 months:

| Segment | In base | Logo retention | NRR | GRR | Benchmark |
|---|---|---|---|---|---|
| Tier: Starter | 381 | 75.1% | 74.8% | 70.0% | NRR below "good" (90) |
| Tier: Growth | 315 | 81.3% | 93.0% | 79.9% | NRR "good" |
| Tier: Enterprise | 90 | 86.9% | 102.5% | 88.2% | NRR below enterprise "good" (110) |
| Contract: monthly | 520 | 76.2% | 86.7% | 78.1% | |
| Contract: annual | 283 | 82.7% | 102.4% | 87.3% | |
| Contract: usage | 62 | 84.5% | 96.1% | 82.4% | |
| Sector, best: Construction | 86 | 84.8% | 111.6% | 88.6% | |
| Sector, worst: Media | 63 | 72.8% | 80.0% | 72.3% | |
| Owner, range | 112 to 146 | 76.9 to 81.5% | 89.1 to 99.4% | | |

Revenue share by tier: Enterprise 48.7 percent on 107 paying customers (mean TTM $180,176),
Growth 30.8 on 344, Starter 9.0 on 526 (mean $6,743). Plan tier predicts the money: mean MRR
$15,195 / $3,197 / $739. Sectors run from Energy at 11.7 percent to Media at 6.2; owners from
21.1 to 11.0.

**Thesis leg 1, annual and upper-tier contracts drive retention and expansion: holds.** Retention
and NRR rise monotonically with tier and are higher on annual than on monthly contracts.

**Thesis leg 2, the acquired books retain as well as organic: fails, and only the schedules
show it.** Nothing in the five files identifies an acquired account. With
`acquisition_schedules.csv` matched to billing by name (Northgate 54 of 63, Pelham 45 of 54,
Vireo 35 of 47):

| Origin | In base | Logo retention | NRR | GRR |
|---|---|---|---|---|
| Organic | 756 | 79.7% | 96.3% | 83.4% |
| Northgate (closed 2024-02-29) | 46 | 76.7% | 101.7% | 88.2% |
| Pelham (closed 2024-10-31) | 44 | 73.3% | 98.3% | 87.6% |
| Vireo (closed 2025-05-30) | 19 | 52.2% | 56.6% | 45.1% |

The fingerprints in the data before the schedules arrive: first invoices bump to 92, 93 and 85
in the quarters after the three closes against a 51 to 62 run rate, and 233 matched billing
customers have a CRM created date more than a year before their first invoice (the migration
preserved original contract dates).

**The mix shift.** Starter's share of organic cohorts: 52.9 percent in 2023, 55.7 in 2024, 56.0
in 2025, 70.3 in 2026, while paid search spend grew 2.6x. Retention inside a contract type is
flat across cohort years (section 5). A board reading the blended cohort curve sees retention
softening; the audit sees the acquisition mix moving down-market.

## 8. Data condition

| File | Primary key | Rows | Distinct entities | Shared key |
|---|---|---|---|---|
| crm_accounts | account_id | 1,464 | 1,400 | none |
| billing_customers | customer_ref | 1,399 | 1,354 | none |
| billing_invoices | invoice_id | 18,149 | 1,399 customers | customer_ref, to billing only |
| product_usage | (org_slug, event_date) | 268,436 | 1,443 | none |
| marketing_spend | (month, channel) | 282 | 6 channels | none |
| board_kpis | month | 46 | | none |
| acquisition_schedules | (book, customer) | 160 | | none: the seller's spelling |

- `email_domain`: 59 domains for 1,464 rows; `nightingale.com` covers 38 companies.
- Duplicates: 0 rows share an `account_id`; 64 folded name keys have two rows; 40 billing
  parent keys are billed as two or more customers.
- Coverage after both resolver tiers: 120 billing customers with no CRM account, 152 CRM
  accounts with no billing customer, 140 usage organizations with no billing match, 59 with no
  CRM match, 0 invoices pointing at an unknown customer, 0 billing customers never invoiced.
- Telemetry before the first invoice: 1 organization (an outlier), against 244 in company 1.
- Invoice statuses: paid 91.8 percent of gross, void 3.1, failed 2.7, refunded 2.3.
- Fields with a history: `account_status` and `mrr_usd` overwritten in place, 0 months
  reconstructible; `lead_source` 26 months; invoices and spend 47; telemetry 48.

**The board pack against the systems** (`board_vs_systems_monthly`, 46 months):

| | |
|---|---|
| Customer count, board over billing's recognized payers | +16.6 percent on average; +11.5 to +16.9 in the last five months |
| MRR, board over billing's recognized revenue | +35.3 percent on average (the early months are inflated by legacy accounts counted before they were invoiced); +6.5 to +9.3 in the last five months |
| Revenue basis | cash for 29 months (Oct 2022 to Feb 2025, prepared by J.R.), recognized for 17 (Mar 2025 on, prepared by M.K.); found by arithmetic, and the switch is recorded only as a note in the March 2025 row |
| Manual adjustments | five months: -14 duplicates removed, +9 annuals reinstated, -22 Pelham migration excluded, +11 Vireo accounts added, -6 test accounts removed |
| Prepared | on average 36 days after the month starts, by two people |

The board count comes from whatever the CRM said on the day the deck was built. The CRM has no
history, so no month of the board series can be reproduced from any system, and every
initiative planned off those numbers inherits the step that produced them.

## 9. What the audit would tell the committee

Not the story yet; the sentences the story will be built from.

1. The defended count is 954, on a written definition. The pack says 1,050 and the CRM says
   892; both are honest and neither is reproducible.
2. Concentration is not the risk: top ten at 19 percent, no customer above 4 percent. How the
   top ten are held is: five of the ten can leave on thirty days' notice.
3. Blended NRR of 96.5 percent is mid-market "good". It is 103 percent in Enterprise and 75 in
   Starter, and the new-customer mix is moving toward Starter fast.
4. Thesis leg 1 holds. Thesis leg 2 fails on the schedules the seller produced on request, with
   Vireo at 52 percent logo retention; it could not have been tested from the systems alone.
5. CAC has risen from about $19,000 to about $27,000 per new billing customer while the
   customers being bought got smaller; payback stretches to 14 months on monthly contracts.
6. The board pack's revenue line changed basis in March 2025 without saying so, its customer
   count runs about 16 percent above billing, and five of 46 months were adjusted by hand. That
   is the data condition finding, and it sets the ceiling on the operating plan until the
   definitions are written down and the CRM gets a history.
