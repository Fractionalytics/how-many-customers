# Solutions: Halyard Systems

**This spoils the exercise. Run the audit first.** Every number below was produced by
`python audit/run.py company2`, `node audit/malloy/run.js company2`, or the generator's own
report, against seed 20260903, as of 2026-08-20.

## The referee

The generator simulated each company's actual state and wrote only the proxies for it into the
files. That state is the referee. It scores the rules; it is not itself a rule.

| | |
|---|---|
| Companies ever | 1,454 (140 legacy, migrated onto Stripe in Q4 2022; 1,154 organic; 160 acquired) |
| Genuinely live | **961**, of which 49 are dormant (paying, not using) |
| Churned | 493 |
| Live MRR | $3,759,773, an ARR of $45.1M |
| By tier, live | Starter 474 logos (49%) on 8% of MRR; Growth 376 (39%) on 34%; Enterprise 111 (12%) on 58% |
| Top 1 / top 10 customers | 3.6% / 21.6% of live MRR |

## The defensible answers to "how many customers?"

| Definition | Answer | Why it is wrong, and why it is defensible anyway |
|---|---|---|
| CRM `mrr_usd > 0` and not Churned, rows | **1,110** | The highest, and 149 above the referee. `mrr_usd` is never zeroed: 215 of the 326 rows marked Churned still carry an MRR, and so do the Inactive and blank ones |
| CRM `mrr_usd > 0` and not Churned, entities | 1,076 | Same, minus the 34 folded duplicates |
| Billing: paid invoice in the last 365 days | 1,066 | Counts everyone who churned in the last year |
| Billing: contract-aware (monthly and usage paid in 90 days, annual in 365) | **954** | Closest to the referee, 7 under it. Misses live customers between a failed and a retried invoice |
| Product: any usage in the last 30 days | 932 | Churned organizations keep logging in for up to 40 days; dormant ones never show |
| Product: monthly active organizations, July | 939 | |
| CRM `account_status = Active`, rows | **892** | 69 under the referee: 112 blank rows and 134 Inactive rows include live customers nobody re-touched |
| CRM Active, entities | 884 | |
| Billing: recognized revenue > 0 in August | 728 | August is a partial month |
| Billing: paid invoice in the last 90 days | **691** | The most rigorous-sounding rule and the worst answer, 270 under. 356 of the 411 annual customers last paid more than 90 days ago, 263 of them between 91 and 365 days ago, which is what a current annual customer looks like |
| Billing: paid in the last 90 days, parent entity | 674 | |

Spread between the four rules a company actually uses: **691 to 1,110**, 419 customers, 61
percent of the lowest. The defended count the audit lands on is the contract-aware billing
rule, stated with its definition, and it is still seven short.

## The designed truths, and where the audit sees them

1. **Tier and contract drive retention and expansion.** Twelve-month logo retention over the
   last 24 base months: Starter 75.1, Growth 81.3, Enterprise 86.9. NRR: 74.8, 93.0, 102.5. By
   contract: monthly 76.2 logo and 86.7 NRR, annual 82.7 and 102.4. The referee's own twelve-month
   organic logo retention by tier is 65.4 / 73.7 / 91.1 and its NRR 76.9 / 96.2 / 104.4 (the audit's
   24-month base window includes the long-tenured legacy book, which lifts every tier). Plan tier
   predicts the money: mean MRR $15,195 / $3,197 / $739.
2. **The acquired books retain worse, and it is only testable with the schedules.** Nothing in
   the five files identifies an acquired account; the migration preserved original contract
   dates. With `acquisition_schedules.csv` (matched to billing by name at 86 / 83 / 75 percent):
   twelve-month logo retention Northgate 76.7, Pelham 73.3, Vireo 52.2, against organic 79.7;
   Vireo's NRR is 56.6. The referee's acquired-versus-organic twelve-month retention is 68.1
   against 65 to 91 by tier. The fingerprint in billing is a bump in first invoices in the quarter
   after each close (92 in 2024 Q1, 93 in 2024 Q4, 85 in 2025 Q2 against a 51 to 62 run rate), and
   233 matched customers whose CRM created date precedes their first invoice by more than a year.
3. **Mix shift.** Starter's share of organic cohorts: 52.9 percent in 2023, 55.7 in 2024, 56.0 in
   2025, **70.3 in 2026**, as paid search spend grew 2.6x. Within a contract type, twelve-month
   logo retention is flat across cohort years (monthly 64.5 / 65.4 / 64.2 for 2023 / 2024 / 2025
   cohorts); the blended number drifts because the mix does.
4. **Concentration.** Top ten customers 19.4 percent of TTM paid revenue, top 20 percent of
   customers 75.9 percent, largest 3.9 percent, HHI 70 (effective count 142). Two of the top ten,
   Verdigris Pioneer Holdings and Acme Onyx, are on monthly contracts, and three are on usage
   contracts; five of the ten are not locked in. The CRM's top ten is a different list (it puts
   Oakfield Compass Labs first and includes Harborview Quantum Holdings, which billing does not).
5. **The board tab.** 46 months prepared, on average 36 days after the month start, by two
   controllers. The customer count runs 16.6 percent above billing's recognized payers on average.
   The revenue line is cash for 29 months and recognized for 17, switching in March 2025 with the
   new preparer, and no row says so beyond a note that month. Five months carry a hand adjustment
   (-14, +9, -22, +11, -6) with a note and no reproducibility.
6. **Telemetry** holds the full 48 months, is gated on the platform start and the churn date, and
   decays over the 90 days before a churn. Zero organizations use the product more than a month
   before their first invoice (one outlier).
7. **The legacy migration cohort.** 185 first invoices in 2022 Q4 against a 51 to 62 run rate,
   because 140 legacy customers were re-invoiced on Stripe. That cohort retains best (80.0 percent
   at month 12 against 63 to 70 for the rest) because it is survivors, and it makes 2022 Q4's CAC
   read $8,850 against $19,000 to $30,000 everywhere else.

## The traps carried over from company 1, with this company's numbers

1. **No shared key** across five files; spend has no account key at all (0 of 282 rows).
2. **`email_domain` is not a key**: 59 domains for 1,464 rows; `nightingale.com` covers 38 companies.
3. **Name variants.** The accent-blind join matches 1,026 of 1,464 CRM rows; folding accents
   matches 1,145 and inflates the row count to 1,484, because folded keys collide (Hernandez
   Retail four ways). The more correct join is the one that trips the alarm.
4. **Diacritics**: 8 percent of companies. Billing strips them; the CRM keeps them.
5. **Near-collisions**: Stonebridge Pioneer six ways, Tanglewood Anchor five. A fuzzy matcher
   merges them.
6. **Entity duplicates**: 0 rows share an `account_id`; 64 folded name keys have two rows.
7. **Subsidiaries**: 40 parent keys billed as two or more customers (45 surplus rows).
8. **Annual contracts** against a 90-day rule: see the 691.
9. **Dormant customers**: 49 paying and not using; the audit sees 75 paying-not-using in July
   through the resolver.
10. **Invoice statuses**: paid 91.8 percent of gross, void 3.1, failed 2.7, refunded 2.3. Failed
    invoices are retried and voids reissued, so the paid ledger is close to complete.
11. **Blank `account_status`**: 112 rows, average MRR $2,210, not the same as Inactive.
12. **Coverage cliffs**: 120 billing customers with no CRM match after both resolver tiers, 152
    CRM accounts with no billing match, 140 usage organizations with no billing match.
13. **Spend joins to nothing**: $30.78M across 47 months and six channels.
14. **Vocabulary**: finance 6 channels, sales 23 `lead_source` values.
15. **`lead_source` blank on 802 of 1,464 rows**; 97.8 percent blank before 2024-06-01.
16. **The acquired book leaves no CRM spike**, and the spike test that worked on company 1 is now
    fooled the other way: the CRM's created dates run back to 2016, so the median month holds 7
    accounts and every billing-era month looks like a spike. Restrict the test to the billing era.

New here: **17. `mrr_usd` is never zeroed** (the 1,110). **18. The entity resolver's tier 2 refuses
the accented families** (Andre Freres, Perez Group, Hernandez Retail, Guimaraes Log, Sao Bento, each
with eight to ten distinct CRM companies behind a two-word billing name), so the unmatched
residue is biased toward the Latin American and Iberian book exactly as in company 1.

## The revenue question

| Basis | TTM |
|---|---|
| Billing, paid cash | $39,592,455 |
| Billing, recognized | $37,295,330 |
| CRM Active x `mrr_usd` x 12 | $39,781,856 |
| CRM not Churned and `mrr_usd` > 0, x 12 | $46,321,248 |

## What a good answer looks like

- states a defended count with its definition, and says how far each other rule is from it
- runs concentration on the invoices, then on the CRM, and says which list the buyer should price
- uses the recognized basis for every customer metric and shows the cash basis once as the trap
- keys cohorts on months since first revenue and calls out the migration cohort
- reads the mix shift as an acquisition-targeting problem, not a churn problem
- asks for the acquisition schedules and refuses to test thesis leg 2 without them
- reconciles the board tab month by month and finds the basis switch by arithmetic
