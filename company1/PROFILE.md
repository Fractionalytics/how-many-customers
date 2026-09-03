# Company 1: Corvane Labs, Inc.

The context a data diligence memo would open with. Everything here is invented and consistent
with the generated files; nothing is a real company or a real person.

| | |
|---|---|
| Legal name | Corvane Labs, Inc. (Delaware C-corp) |
| Headquarters | Raleigh, North Carolina |
| Founded | March 2021 |
| Product | Operations workflow software for mid-sized companies: scheduling, approvals, field reporting. Sold by seat, in three plan tiers |
| General availability | September 2022 (the first CRM account is dated 2022-09-09; the first invoice 2022-10-27) |
| Employees | 96 as of August 2026 (41 engineering and product, 27 sales and marketing, 18 customer success and support, 10 G&A) |
| Ownership | Venture-backed. Seed 2021, Series A 2023, Series B 2025. The B lead has board control and is running a sale process |
| Systems | Salesforce (CRM), Stripe (billing), in-house product telemetry, marketing spend in the GL by channel. No data warehouse; reporting is assembled by hand monthly |
| As-of date for the data | 2026-08-20 |

## Acquisition history

Three small books were bought for their customer lists. Each was migrated onto Corvane's CRM and
billing within about ten weeks of close, and the migration set each account's created date to
the date the contract was re-papered, not to a single migration day, so the books do not appear
as a spike anywhere.

| Book | Closed | Accounts migrated | Contracts re-papered |
|---|---|---|---|
| Vireo (a scheduling tool, Charlotte) | October 2022 | 45 | 2022-10-21 to 2022-12-25 |
| Northgate (a field-reporting app, Columbus) | July 2023 | 63 | 2023-07-08 to 2023-09-03 |
| Pelham (an approvals workflow, Pittsburgh) | October 2024 | 52 | 2024-10-18 to 2024-12-02 |

None of the three cost anything to acquire on the marketing side, and nothing in the five data
files identifies them. The migration script had to put something in `lead_source`, so 33 of the
160 carry a marketing channel they never came from.

## What the data was built to test

The customer count. Four systems, no shared key, and several defensible answers to "how many
customers do we have?" that disagree by hundreds on a book of about twelve hundred. See
`README.md` for the setup and `SOLUTIONS.md` for the referee's answers and the sixteen traps.

## Audit status

The full customer base audit and data condition review were run against this company on
2026-09-02 (`FINDINGS.md`, outputs in `out/`). The audit found the company's lifecycle model too
simple to carry a story (no churn before September 2024, telemetry that ignores the signing date,
segments that are independent draws, MRR capped near $10K, two-month payback), which is why
company 2 exists. Company 1 stays exactly as it was audited.

## Referee summary

758 genuinely live customers as of 2026-08-20 (135 paused, 307 churned), on a book of 1,200
companies. The generator knows this; no file records it.
