# Company 2: Halyard Systems, Inc.

The context a data diligence memo would open with. Everything here is invented and consistent
with the generated files; nothing is a real company, fund or person.

| | |
|---|---|
| Legal name | Halyard Systems, Inc. (Delaware C-corp) |
| Headquarters | Denver, Colorado |
| Founded | April 2016 |
| Product | Field-operations software for mid-sized operators: crew scheduling, approvals, field reporting, compliance logs. Sold by seat in three plan tiers (Starter, Growth, Enterprise), on monthly, annual or usage-based contracts |
| Customers | About 960 live as of August 2026, on a book of roughly 1,450 companies that have ever paid. Sectors: logistics, construction, healthcare, energy, retail, hospitality, manufacturing, media, education, fintech |
| Revenue | About $45M of recognized annual run-rate; $39.6M of paid invoices in the trailing twelve months |
| Employees | 212 as of August 2026 (78 engineering and product, 61 sales and marketing, 44 customer success and support, 29 G&A) |
| Ownership | Bootstrapped to 2019, Series A 2019, Series B 2021. **Bramblewood Capital Partners** bought a majority in November 2023 as a platform investment and has since closed three add-ons. Bramblewood is running a sale process; the reader of the audit is the buyer's investment committee |
| Systems | Salesforce (CRM, since 2017), Stripe (billing, since October 2022; the previous system was not migrated), in-house product telemetry (retained in full), marketing spend by channel in the GL. No data warehouse. The board pack is assembled monthly in a spreadsheet by the controller |
| As-of date for the data | 2026-08-20 |

## Timeline

| When | What |
|---|---|
| 2016-04 | Founded. Product GA 2017 |
| 2017 to 2022 | Grows to about 140 customers on a home-grown billing system. Salesforce adopted 2017 |
| 2022-10 | Stripe goes live. The 140 legacy customers are re-invoiced on Stripe over the following quarter; their CRM records keep their original dates, their invoice history starts here |
| 2023-11 | Bramblewood takes a majority |
| 2024-02-29 | Acquires **Northgate** (a field-reporting app, Columbus, Ohio): 63 customers |
| 2024-06 | `lead_source` field added to Salesforce; everything before it is blank |
| 2024-10-31 | Acquires **Pelham** (an approvals workflow, Pittsburgh, Pennsylvania): 52 customers |
| 2025-03 | New controller. The board pack's revenue line switches from cash collected to Stripe's recognized figure. Nobody records the change on the pack itself |
| 2025-05-30 | Acquires **Vireo** (a crew-scheduling tool, Charlotte, North Carolina): 45 customers |
| 2025 onward | Paid search budget more than doubles; self-serve Starter signups rise from about half of new customers to about seventy percent |
| 2026-08-20 | Data cut for the sale process |

## The three acquisitions

Each book was migrated into Salesforce and Stripe in the quarter after close. The migration
preserved each account's **original contract date** as its CRM created date, which is good
practice and which also means a bought book leaves no spike in the CRM. In billing, each book
shows up as a bump in first invoices in the quarter after close, as contracts were re-papered.
The migration script had to put something in `lead_source`, so some acquired accounts carry a
marketing channel they never came from.

The seller produced `acquisition_schedules.csv` on request: book, close date, customer name in
the seller's spelling, original contract date, and annual contract value at close.

## What the buyer's thesis says, and what the data was built to test

The thesis under diligence: **annual mid-market contracts drive retention and expansion, and the
three acquired books retain as well as the organic base.** The first leg is designed to hold.
The second is designed to fail, and to be testable only once the schedules are in hand.

Beyond the thesis, the fixture was built so that a customer base audit and a data condition
review each find something a board pack would miss. `SOLUTIONS.md` has the referee's answers.

## What "customer" means here, and why it is contested

Four systems hold a proxy for it and none holds the fact. Salesforce has a hand-maintained
status and a typed-in MRR field. Stripe has invoices, on three contract cadences. The telemetry
has organizations that log in. The board pack has a number the controller assembled on the
sixth of the month. They disagree by hundreds, and every one of them is defensible.
